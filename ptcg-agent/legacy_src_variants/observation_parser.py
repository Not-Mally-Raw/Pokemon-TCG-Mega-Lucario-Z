"""
PTCG AI Agent — Observation Parser (v2: Rebuilt from verified API docs)
======================================================================

CRITICAL CHANGE LOG (v1 → v2):
    This is a COMPLETE REWRITE. v1 was built from guessed field names.
    v2 is built from verified cabt Engine 0.1.0 API documentation at:
        https://matsuoinstitute.github.io/cabt/api.html

    What changed and why:
    1. Observation.select is a SIBLING of Observation.current, not nested.
       v1 looked for observation['current']['legal']. Wrong key, wrong level.
    2. Agent return type is list[int], not int. Some decisions require
       selecting MULTIPLE options (minCount/maxCount on SelectData).
    3. Options carry (OptionType, AreaType, index, playerIndex), NOT
       card names/descriptions. There is no natural-language layer.
    4. Runtime Pokemon objects are THIN: id, serial, hp, maxHp, energies,
       energyCards, tools, preEvolution, appearThisTurn. No name, attacks,
       weakness, resistance. Those live in static CardData from all_card_data().
    5. Card IDs are int, not str. Deck.csv is one int per line.
    6. PlayerState has explicit handCount/deckCount fields. Opponent's hand
       is None, not an integer. handCount is always available for both players.
    7. Status conditions (poisoned, burned, asleep, paralyzed, confused) are
       flat booleans on PlayerState, not a list on each card.
    8. SelectContext has 49 members, not 31. The 18 missing ones include
       MULLIGAN and IS_FIRST — needed on game turn 1.
    9. OptionType enum was entirely absent from v1. It's the only way to
       distinguish PLAY from ATTACK from RETREAT from END.

PIPELINE STAGE: Stage 1 — Perception
    Raw obs_dict → to_observation_class(obs_dict) → ParsedObservation

REFERENCE:
    cabt API: https://matsuoinstitute.github.io/cabt/api.html
    Sim module: https://matsuoinstitute.github.io/cabt/sim.html
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum, IntEnum


# =============================================================================
# Section 1: Enums — Verified against cabt Engine 0.1.0 API docs
# =============================================================================
# SOURCE: https://matsuoinstitute.github.io/cabt/api.html#enums
#
# We mirror these so the agent can be unit-tested WITHOUT the cabt library.
# At submission time, cg.api.* enums exist in the runtime. Our code compares
# by .value (string) to be safe against int vs enum serialization differences.


class OptionType(Enum):
    """
    What kind of action an option represents.
    
    CRITICAL: v1 had NO OptionType at all. This is the ONLY way to tell
    a PLAY action from an ATTACK from a RETREAT from an END_TURN.
    Without this, heuristic dispatch is blind.
    """
    YES = "YES"
    NO = "NO"
    CARD = "CARD"
    NUMBER = "NUMBER"
    END = "END"           # End turn
    PLAY = "PLAY"         # Play a card from hand
    ATTACK = "ATTACK"     # Use an attack
    RETREAT = "RETREAT"   # Retreat active Pokémon
    EVOLVE = "EVOLVE"     # Evolve a Pokémon
    SKILL = "SKILL"       # Use an ability


class SelectType(Enum):
    """What kind of selection the engine is asking for. 11 members, verified."""
    MAIN = "MAIN"
    CARD = "CARD"
    ATTACHED_CARD = "ATTACHED_CARD"
    CARD_OR_ATTACHED_CARD = "CARD_OR_ATTACHED_CARD"
    ENERGY = "ENERGY"
    SKILL = "SKILL"
    ATTACK = "ATTACK"
    EVOLVE = "EVOLVE"
    COUNT = "COUNT"
    YES_NO = "YES_NO"
    SPECIAL_CONDITION = "SPECIAL_CONDITION"


class SelectContext(Enum):
    """
    The game situation in which the selection is being made.
    
    Verified 49 members from cabt api.html.
    """
    ACTIVATE = "ACTIVATE"
    AFFECT_SPECIAL_CONDITION = "AFFECT_SPECIAL_CONDITION"
    ATTACH_FROM = "ATTACH_FROM"
    ATTACH_TO = "ATTACH_TO"
    ATTACK = "ATTACK"
    COIN_HEAD = "COIN_HEAD"
    DAMAGE = "DAMAGE"
    DAMAGE_COUNTER = "DAMAGE_COUNTER"
    DAMAGE_COUNTER_ANY = "DAMAGE_COUNTER_ANY"
    DAMAGE_COUNTER_COUNT = "DAMAGE_COUNTER_COUNT"
    DETACH_FROM = "DETACH_FROM"
    DEVOLVE = "DEVOLVE"
    DISABLE_ATTACK = "DISABLE_ATTACK"
    DISCARD = "DISCARD"
    DISCARD_CARD_OR_ATTACHED_CARD = "DISCARD_CARD_OR_ATTACHED_CARD"
    DISCARD_ENERGY = "DISCARD_ENERGY"
    DISCARD_ENERGY_CARD = "DISCARD_ENERGY_CARD"
    DISCARD_TOOL_CARD = "DISCARD_TOOL_CARD"
    DRAW_COUNT = "DRAW_COUNT"
    EFFECT_TARGET = "EFFECT_TARGET"
    EVOLVE = "EVOLVE"
    EVOLVES_FROM = "EVOLVES_FROM"
    EVOLVES_TO = "EVOLVES_TO"
    FIRST_EFFECT = "FIRST_EFFECT"
    HEAL = "HEAL"
    IS_FIRST = "IS_FIRST"
    LOOK = "LOOK"
    MAIN = "MAIN"
    MORE_DEVOLVE = "MORE_DEVOLVE"
    MULLIGAN = "MULLIGAN"
    NOT_MOVE = "NOT_MOVE"
    RECOVER_SPECIAL_CONDITION = "RECOVER_SPECIAL_CONDITION"
    REMOVE_DAMAGE_COUNTER = "REMOVE_DAMAGE_COUNTER"
    REMOVE_DAMAGE_COUNTER_COUNT = "REMOVE_DAMAGE_COUNTER_COUNT"
    SETUP_ACTIVE_POKEMON = "SETUP_ACTIVE_POKEMON"
    SETUP_BENCH_POKEMON = "SETUP_BENCH_POKEMON"
    SKILL_ORDER = "SKILL_ORDER"
    SWITCH = "SWITCH"
    SWITCH_ENERGY = "SWITCH_ENERGY"
    SWITCH_ENERGY_CARD = "SWITCH_ENERGY_CARD"
    TO_ACTIVE = "TO_ACTIVE"
    TO_BENCH = "TO_BENCH"
    TO_DECK = "TO_DECK"
    TO_DECK_BOTTOM = "TO_DECK_BOTTOM"
    TO_DECK_ENERGY = "TO_DECK_ENERGY"
    TO_FIELD = "TO_FIELD"
    TO_HAND = "TO_HAND"
    TO_HAND_ENERGY = "TO_HAND_ENERGY"
    TO_PRIZE = "TO_PRIZE"
    SPECIAL_CONDITION_CURE = "SPECIAL_CONDITION_CURE"  # [NEW] Choose condition to cure


class CardType(Enum):
    """Types of cards in the PTCG. 7 members, verified."""
    POKEMON = "POKEMON"
    ITEM = "ITEM"
    TOOL = "TOOL"
    SUPPORTER = "SUPPORTER"
    STADIUM = "STADIUM"
    BASIC_ENERGY = "BASIC_ENERGY"
    SPECIAL_ENERGY = "SPECIAL_ENERGY"


class AreaType(Enum):
    """Board zones where cards can exist. 12 members, verified."""
    DECK = "DECK"
    HAND = "HAND"
    DISCARD = "DISCARD"
    ACTIVE = "ACTIVE"
    BENCH = "BENCH"
    PRIZE = "PRIZE"
    STADIUM = "STADIUM"
    ENERGY = "ENERGY"
    TOOL = "TOOL"
    PRE_EVOLUTION = "PRE_EVOLUTION"
    PLAYER = "PLAYER"
    LOOKING = "LOOKING"


class EnergyType(Enum):
    """Pokémon energy types. 12 members, verified."""
    COLORLESS = "COLORLESS"
    GRASS = "GRASS"
    FIRE = "FIRE"
    WATER = "WATER"
    LIGHTNING = "LIGHTNING"
    PSYCHIC = "PSYCHIC"
    FIGHTING = "FIGHTING"
    DARKNESS = "DARKNESS"
    METAL = "METAL"
    DRAGON = "DRAGON"
    RAINBOW = "RAINBOW"
    TEAM_ROCKET = "TEAM_ROCKET"


class SpecialConditionType(Enum):
    """Status conditions. 5 members, verified."""
    POISON = "POISON"
    BURN = "BURN"
    SLEEP = "SLEEP"
    PARALYZE = "PARALYZE"
    CONFUSE = "CONFUSE"


# =============================================================================
# Section 2: Parsed Data Structures — Rebuilt to match real API objects
# =============================================================================
# The old CardInfo tried to be a "rich card with attacks and abilities."
# In reality, runtime Pokemon objects are THIN. The rich metadata lives
# in a SEPARATE static table (CardData) accessed via all_card_data().
# We split accordingly:
#   - PokemonState: mirrors api.Pokemon (runtime, thin)
#   - CardData: mirrors sim.CardData (static, rich) — loaded once via cache
#   - ResolvedPokemon: PokemonState + CardData joined on card_id


@dataclass
class PokemonState:
    """
    A Pokémon as it exists on the board at runtime.
    
    Mirrors api.Pokemon. This is THIN — it has hp and energy counts,
    but NOT name, attacks, weakness, or resistance. Those come from
    CardData (see card_database.py).
    
    CRITICAL DIFFERENCE from v1's CardInfo:
        - card_id is int, not str
        - No card_name, attacks, abilities, weakness, resistance, retreat_cost
        - energies is a list (energy type counts), energyCards is Card references
        - tools is a list of attached tool Card references
        - preEvolution is nested PokemonState(s)
        - appear_this_turn is a boolean
    """
    card_id: int = 0                # Maps to CardData.cardId for static lookup
    serial: int = 0                 # Unique board instance ID (tracks individual cards)
    hp: int = 0                     # Current HP
    max_hp: int = 0                 # Maximum HP
    energies: List[int] = field(default_factory=list)      # Attached energy types (as int enum values)
    energy_cards: List[int] = field(default_factory=list)   # Attached energy card IDs
    tools: List[int] = field(default_factory=list)          # Attached tool card IDs
    pre_evolution: List[Any] = field(default_factory=list)  # Pre-evolution Pokemon objects
    appear_this_turn: bool = False  # Did this Pokémon enter play this turn?


@dataclass
class ParsedPlayerState:
    """
    One player's board state.
    
    Mirrors api.PlayerState. Key differences from v1:
        - active is a list of 0-or-1 PokemonState (not Optional[CardInfo])
        - hand is a list of card IDs (int), NOT card objects with full metadata
        - hand_count is an explicit field from handCount, NOT derived from len(hand)
        - deck_count is from deckCount, NOT guessed from the 'deck' field
        - Status conditions are flat booleans on THIS object, not on individual cards
        - prize is a list (may contain card objects or be empty)
        - bench_max tracks the dynamic bench limit
    """
    # Board zones
    active: List[PokemonState] = field(default_factory=list)    # 0 or 1 elements
    bench: List[PokemonState] = field(default_factory=list)     # 0 to bench_max
    hand: List[int] = field(default_factory=list)               # Card IDs visible to self
    discard: List[Any] = field(default_factory=list)            # Discard pile (public)
    prize: List[Any] = field(default_factory=list)              # Prize cards
    
    # Counts (always available for BOTH players)
    hand_count: int = 0         # From PlayerState.handCount — works for opponent too
    deck_count: int = 0         # From PlayerState.deckCount
    bench_max: int = 5          # From PlayerState.benchMax (usually 5)
    
    # Status conditions — flat booleans on the PLAYER, not per-card
    # (Only the active Pokémon can have status conditions under PTCG rules)
    poisoned: bool = False
    burned: bool = False
    asleep: bool = False
    paralyzed: bool = False
    confused: bool = False


@dataclass
class ParsedOption:
    """
    A single selectable action from obs.select.option.
    
    CRITICAL DIFFERENCE from v1's LegalOption:
        - NO card_name, NO description. Options are typed indices, not text.
        - 'option_type' tells you WHAT (PLAY, ATTACK, RETREAT, END, CARD, etc.)
        - 'area' tells you WHERE (HAND, BENCH, ACTIVE, DECK, etc.)
        - 'index' tells you WHICH card in that area
        - 'player_index' tells you WHOSE card (0=us, 1=opponent)
        - 'number' is for COUNT-type selections
    
    To get the actual card, you must:
        state.players[player_index].<area>[index] → Pokemon → pokemon.id → CardData
    """
    list_position: int = 0       # Position in the option list (what we return to engine)
    option_type: str = ""        # OptionType value: PLAY, ATTACK, RETREAT, END, etc.
    area: str = ""               # AreaType value: HAND, BENCH, ACTIVE, etc.
    index: int = 0               # Index within the area
    player_index: int = 0        # Which player this option refers to (0 or 1)
    number: int = 0              # For NUMBER-type options


@dataclass
class ParsedSelectData:
    """
    The complete selection context from obs.select.
    
    CRITICAL DIFFERENCE from v1:
        - This is a SIBLING of obs.current, not nested inside it
        - min_count/max_count define how many options to pick (list[int] return)
        - select_type + context define the decision category
        - deck field may contain a separate list of Card objects for deck search
    """
    select_type: str = ""        # SelectType value
    context: str = ""            # SelectContext value
    options: List[ParsedOption] = field(default_factory=list)
    min_count: int = 1           # Minimum selections required
    max_count: int = 1           # Maximum selections allowed
    deck: List[Any] = field(default_factory=list)  # Search deck (when searching)


@dataclass
class ParsedObservation:
    """
    The complete parsed game state at a single decision point.
    
    STRUCTURAL FIX from v1:
        Observation has THREE top-level siblings:
            1. obs.current  → State (board state, player states)
            2. obs.select   → SelectData (legal actions) — may be None!
            3. obs.logs     → list (game event log)
        
        v1 had select nested inside current. That's the critical bug.
    
    When obs.select is None, we are in the INITIAL SETUP PHASE and must
    return our 60-card deck as list[int]. This is NOT a decision point —
    it's a deck submission call. The agent entrypoint must check for this
    BEFORE calling the parser.
    """
    # From obs.current (State)
    your_index: int = 0          # Which player are we? (State.yourIndex)
    my_state: ParsedPlayerState = field(default_factory=ParsedPlayerState)
    opp_state: ParsedPlayerState = field(default_factory=ParsedPlayerState)
    
    # From obs.select (SelectData) — None means deck submission phase
    select: Optional[ParsedSelectData] = None
    is_setup_phase: bool = False  # True when obs.select is None
    
    # From obs.logs
    logs: List[Any] = field(default_factory=list)


# =============================================================================
# Section 3: Safe extraction utility
# =============================================================================

def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """
    Safely extract a field from a dict-like or object-like source.
    
    RETAINED from v1: This defensive pattern is correct. The cabt observation
    arrives as a Python object (from to_observation_class), but during
    serialization/deserialization through kaggle_environments it may arrive
    as a dict. We handle both.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _safe_int(val: Any, default: int = 0) -> int:
    """Safely convert to int, handling None, empty strings, etc."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_bool(val: Any, default: bool = False) -> bool:
    """Safely convert to bool."""
    if val is None:
        return default
    try:
        return bool(val)
    except (ValueError, TypeError):
        return default


# =============================================================================
# Section 4: Parser functions — Built against verified schema
# =============================================================================

def _parse_pokemon(raw: Any) -> PokemonState:
    """
    Parse a runtime Pokemon object into PokemonState.
    
    Real api.Pokemon fields:
        id: int, serial: int, hp: int, maxHp: int,
        energies: list, energyCards: list, tools: list,
        preEvolution: list, appearThisTurn: bool
    """
    if raw is None:
        return PokemonState()
    
    poke = PokemonState()
    poke.card_id = _safe_int(_safe_get(raw, 'id', _safe_get(raw, 'cardId', 0)))
    poke.serial = _safe_int(_safe_get(raw, 'serial', 0))
    poke.hp = _safe_int(_safe_get(raw, 'hp', 0))
    poke.max_hp = _safe_int(_safe_get(raw, 'maxHp', _safe_get(raw, 'max_hp', 0)))
    poke.appear_this_turn = _safe_bool(_safe_get(raw, 'appearThisTurn',
                                                  _safe_get(raw, 'appear_this_turn', False)))
    
    # Energies: list of energy type values (ints or enum values)
    raw_energies = _safe_get(raw, 'energies', [])
    if isinstance(raw_energies, (list, tuple)):
        poke.energies = list(raw_energies)
    
    # Energy cards: list of attached energy card objects → extract IDs
    raw_energy_cards = _safe_get(raw, 'energyCards', _safe_get(raw, 'energy_cards', []))
    if isinstance(raw_energy_cards, (list, tuple)):
        poke.energy_cards = [_safe_int(_safe_get(ec, 'id', _safe_get(ec, 'cardId', ec)))
                             for ec in raw_energy_cards]
    
    # Tools: list of attached tool card objects → extract IDs
    raw_tools = _safe_get(raw, 'tools', [])
    if isinstance(raw_tools, (list, tuple)):
        poke.tools = [_safe_int(_safe_get(t, 'id', _safe_get(t, 'cardId', t)))
                      for t in raw_tools]
    
    # Pre-evolution: recursive, but we just store raw for now
    raw_pre = _safe_get(raw, 'preEvolution', _safe_get(raw, 'pre_evolution', []))
    if isinstance(raw_pre, (list, tuple)):
        poke.pre_evolution = [_parse_pokemon(p) for p in raw_pre]
    elif raw_pre is not None:
        poke.pre_evolution = [_parse_pokemon(raw_pre)]
    
    return poke


def _parse_pokemon_list(raw_list: Any) -> List[PokemonState]:
    """Parse a list of Pokemon objects."""
    if not raw_list or not isinstance(raw_list, (list, tuple)):
        return []
    return [_parse_pokemon(p) for p in raw_list if p is not None]


def _parse_player_state(raw_player: Any) -> ParsedPlayerState:
    """
    Parse a player's state from the observation.
    
    Real api.PlayerState fields:
        active: list[Pokemon] (0 or 1)
        bench: list[Pokemon] (0 to benchMax)
        hand: list[Card] (visible to self, None for opponent)
        handCount: int (always available)
        deckCount: int (always available)
        discard: list[Card]
        prize: list[Card]
        benchMax: int
        poisoned, burned, asleep, paralyzed, confused: bool
    
    KEY DIFFERENCE from v1:
        - handCount is an EXPLICIT field, NOT derived from len(hand)
        - hand is None for the opponent, not an integer
        - Status conditions are flat booleans HERE, not per-card
    """
    if raw_player is None:
        return ParsedPlayerState()
    
    state = ParsedPlayerState()
    
    # Active Pokémon — always a list of 0 or 1
    raw_active = _safe_get(raw_player, 'active', [])
    state.active = _parse_pokemon_list(
        raw_active if isinstance(raw_active, (list, tuple)) else [raw_active] if raw_active else []
    )
    
    # Bench
    state.bench = _parse_pokemon_list(_safe_get(raw_player, 'bench', []))
    
    # Hand — list of card objects for self, None for opponent
    raw_hand = _safe_get(raw_player, 'hand', None)
    if raw_hand is not None and isinstance(raw_hand, (list, tuple)):
        # Self: extract card IDs
        state.hand = [_safe_int(_safe_get(c, 'id', _safe_get(c, 'cardId', c)))
                      for c in raw_hand]
    else:
        state.hand = []
    
    # handCount — EXPLICIT field, always available for BOTH players
    state.hand_count = _safe_int(
        _safe_get(raw_player, 'handCount', _safe_get(raw_player, 'hand_count',
                  len(state.hand) if state.hand else 0))
    )
    
    # deckCount — EXPLICIT field
    state.deck_count = _safe_int(
        _safe_get(raw_player, 'deckCount', _safe_get(raw_player, 'deck_count', 0))
    )
    
    # Discard pile — public information, list of card objects
    raw_discard = _safe_get(raw_player, 'discard', [])
    if isinstance(raw_discard, (list, tuple)):
        state.discard = list(raw_discard)  # Keep raw for now; enrich in Stage 2
    
    # Prize cards
    raw_prize = _safe_get(raw_player, 'prize', [])
    if isinstance(raw_prize, (list, tuple)):
        state.prize = list(raw_prize)
    
    # benchMax
    state.bench_max = _safe_int(_safe_get(raw_player, 'benchMax',
                                          _safe_get(raw_player, 'bench_max', 5)), 5)
    
    # Status conditions — flat booleans on PlayerState
    state.poisoned = _safe_bool(_safe_get(raw_player, 'poisoned', False))
    state.burned = _safe_bool(_safe_get(raw_player, 'burned', False))
    state.asleep = _safe_bool(_safe_get(raw_player, 'asleep', False))
    state.paralyzed = _safe_bool(_safe_get(raw_player, 'paralyzed', False))
    state.confused = _safe_bool(_safe_get(raw_player, 'confused', False))
    
    return state


def _parse_option(raw_option: Any, list_position: int) -> ParsedOption:
    """
    Parse a single Option from obs.select.option.
    
    Real api.Option fields:
        type: OptionType (PLAY, ATTACK, RETREAT, END, CARD, etc.)
        area: AreaType (HAND, BENCH, ACTIVE, etc.)
        index: int (position within that area)
        playerIndex: int (0 or 1)
        number: int (for NUMBER-type options)
    
    CRITICAL: Options do NOT have names or descriptions.
    To get the card identity: state.players[playerIndex].<area>[index] → pokemon.id → CardData
    """
    if raw_option is None:
        return ParsedOption(list_position=list_position)
    
    opt = ParsedOption()
    opt.list_position = list_position
    
    # OptionType — may arrive as enum object, int, or string
    raw_type = _safe_get(raw_option, 'type', '')
    if hasattr(raw_type, 'name'):
        opt.option_type = raw_type.name      # It's an enum → use name
    elif hasattr(raw_type, 'value'):
        opt.option_type = str(raw_type.value)
    else:
        opt.option_type = str(raw_type)
    
    # AreaType — same treatment
    raw_area = _safe_get(raw_option, 'area', '')
    if hasattr(raw_area, 'name'):
        opt.area = raw_area.name
    elif hasattr(raw_area, 'value'):
        opt.area = str(raw_area.value)
    else:
        opt.area = str(raw_area)
    
    opt.index = _safe_int(_safe_get(raw_option, 'index', 0))
    opt.player_index = _safe_int(_safe_get(raw_option, 'playerIndex',
                                           _safe_get(raw_option, 'player_index', 0)))
    opt.number = _safe_int(_safe_get(raw_option, 'number', 0))
    
    return opt


def _parse_select_data(raw_select: Any) -> Optional[ParsedSelectData]:
    """
    Parse obs.select into ParsedSelectData.
    
    Real api.SelectData fields:
        type: SelectType
        context: SelectContext
        option: list[Option]
        minCount: int
        maxCount: int
        deck: list[Card]  (for deck search actions)
    
    Returns None if raw_select is None (= setup phase, return deck).
    """
    if raw_select is None:
        return None
    
    sel = ParsedSelectData()
    
    # SelectType
    raw_type = _safe_get(raw_select, 'type', _safe_get(raw_select, 'selectType', ''))
    if hasattr(raw_type, 'name'):
        sel.select_type = raw_type.name
    elif hasattr(raw_type, 'value'):
        sel.select_type = str(raw_type.value)
    else:
        sel.select_type = str(raw_type)
    
    # SelectContext
    raw_ctx = _safe_get(raw_select, 'context', _safe_get(raw_select, 'selectContext', ''))
    if hasattr(raw_ctx, 'name'):
        sel.context = raw_ctx.name
    elif hasattr(raw_ctx, 'value'):
        sel.context = str(raw_ctx.value)
    else:
        sel.context = str(raw_ctx)
    
    # Options — the key is 'option' (singular), NOT 'options'
    raw_options = _safe_get(raw_select, 'option', _safe_get(raw_select, 'options', []))
    if isinstance(raw_options, (list, tuple)):
        sel.options = [_parse_option(opt, i) for i, opt in enumerate(raw_options)]
    
    # min/max selection counts
    sel.min_count = _safe_int(_safe_get(raw_select, 'minCount',
                                        _safe_get(raw_select, 'min_count', 1)), 1)
    sel.max_count = _safe_int(_safe_get(raw_select, 'maxCount',
                                        _safe_get(raw_select, 'max_count', 1)), 1)
    
    # Deck (for search operations like Ultra Ball, Nest Ball)
    raw_deck = _safe_get(raw_select, 'deck', [])
    if isinstance(raw_deck, (list, tuple)):
        sel.deck = list(raw_deck)
    
    return sel


# =============================================================================
# Section 5: Main entry point
# =============================================================================

def parse_observation(obs: Any) -> ParsedObservation:
    """
    MAIN ENTRY POINT — Stage 1 of the agent pipeline.
    
    Converts the raw observation from the cabt engine into a fully
    typed ParsedObservation.
    
    USAGE IN AGENT:
        def agent(obs_dict: dict) -> list[int]:
            obs = to_observation_class(obs_dict)  # cg.api call
            parsed = parse_observation(obs)
            
            if parsed.is_setup_phase:
                return MY_DECK  # list of 60 card IDs
            
            # ... heuristic/value/MCTS decision logic ...
            return [chosen_option_index]  # list[int], not int!
    
    STRUCTURAL FIX from v1:
        obs.select is a SIBLING of obs.current, not nested inside it.
        obs has three top-level fields: current, select, logs.
    
    This function NEVER raises an exception. On any parse failure,
    it returns a valid ParsedObservation with sensible defaults.
    """
    if obs is None:
        return ParsedObservation(is_setup_phase=True)
    
    parsed = ParsedObservation()
    
    # ─── obs.select (SelectData) ───
    # CRITICAL: This is a TOP-LEVEL sibling of current, not nested.
    # If None → we are in deck submission phase.
    raw_select = _safe_get(obs, 'select', None)
    if raw_select is None:
        parsed.is_setup_phase = True
        parsed.select = None
    else:
        parsed.is_setup_phase = False
        try:
            parsed.select = _parse_select_data(raw_select)
        except Exception:
            parsed.select = ParsedSelectData()  # Empty but valid
    
    # ─── obs.current (State) ───
    # Contains: yourIndex, players[], and game-level state
    raw_current = _safe_get(obs, 'current', None)
    
    if raw_current is not None:
        # Your player index — State.yourIndex
        parsed.your_index = _safe_int(
            _safe_get(raw_current, 'yourIndex',
                      _safe_get(raw_current, 'your_index', 0))
        )
        
        # Player states — State.players[]
        raw_players = _safe_get(raw_current, 'players', [])
        if isinstance(raw_players, (list, tuple)) and len(raw_players) >= 2:
            my_idx = parsed.your_index
            opp_idx = 1 - my_idx
            try:
                parsed.my_state = _parse_player_state(raw_players[my_idx])
            except Exception:
                parsed.my_state = ParsedPlayerState()
            try:
                parsed.opp_state = _parse_player_state(raw_players[opp_idx])
            except Exception:
                parsed.opp_state = ParsedPlayerState()
    
    # ─── obs.logs ───
    raw_logs = _safe_get(obs, 'logs', [])
    if isinstance(raw_logs, (list, tuple)):
        parsed.logs = list(raw_logs)
    
    return parsed


# =============================================================================
# Section 6: Option resolution helpers
# =============================================================================
# These helpers solve the "Option → Card" resolution chain that v1 lacked.
# An option says (area=HAND, index=2, playerIndex=0). To know what card that
# IS, you need: state.players[0].hand[2] → Card → card.id → CardData.

def resolve_option_to_card_id(
    parsed: ParsedObservation,
    option: ParsedOption,
    raw_state: Any = None
) -> Optional[int]:
    """
    Resolve an option's (area, index, playerIndex) to a card ID.
    
    This requires access to the player state. The option tells you
    WHERE to look; the player state tells you WHAT's there.
    
    Args:
        parsed: ParsedObservation with player states
        option: The option to resolve
        raw_state: The raw obs.current object (needed for full card resolution)
    
    Returns:
        card_id (int) if resolvable, None otherwise
    """
    if option.option_type in ("END", "YES", "NO", "NUMBER"):
        return None  # These options don't reference cards
    
    # Determine which player's state to look into
    if option.player_index == parsed.your_index:
        player = parsed.my_state
    else:
        player = parsed.opp_state
    
    area = option.area
    idx = option.index
    
    try:
        if area in ("ACTIVE", AreaType.ACTIVE.value):
            if player.active and idx < len(player.active):
                return player.active[idx].card_id
        elif area in ("BENCH", AreaType.BENCH.value):
            if idx < len(player.bench):
                return player.bench[idx].card_id
        elif area in ("HAND", AreaType.HAND.value):
            if idx < len(player.hand):
                return player.hand[idx]  # hand is already list[int] of card IDs
    except (IndexError, AttributeError):
        pass
    
    return None


def get_option_count_range(parsed: ParsedObservation) -> Tuple[int, int]:
    """
    Get the (min_count, max_count) for how many options to select.
    
    The agent MUST return a list[int] with length between min and max.
    """
    if parsed.select is None:
        return (0, 0)
    return (parsed.select.min_count, parsed.select.max_count)


def get_active_pokemon(parsed: ParsedObservation, mine: bool = True) -> Optional[PokemonState]:
    """Get the active Pokémon for the specified player, or None."""
    state = parsed.my_state if mine else parsed.opp_state
    return state.active[0] if state.active else None
