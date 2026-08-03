"""
PTCG AI Agent - Mega Lucario ex Neuro-Symbolic Hybrid (Kaggle Submission v3.1.1)
Native cg.api engine integration, score-based multi-select action ranking, competitive heuristics.
Last Updated: 2026-07-29 | Patch 5: Macro-Intents + Decision Entropy Telemetry
"""

import sys
import os
import csv
import json
import logging
import math
import random
import re
import numpy as np
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Union

import cg.api as cg
from cg.api import (
    to_observation_class,
    all_card_data,
    AreaType,
    OptionType,
    SelectType,
    CardType,
    EnergyType,
    SelectContext,
    Card,
    Pokemon,
    PlayerState,
    Option,
    Observation,
    Attack,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("ptcg_agent")

# Global Card Database initialized via native cg.api
CARD_DB: Dict[int, Card] = {}


def get_card_db() -> Dict[int, Any]:
    """Build id->CardData map. all_card_data() may return list or dict."""
    global CARD_DB
    if not CARD_DB:
        raw = all_card_data()
        if isinstance(raw, dict):
            CARD_DB = raw
        else:
            # list[CardData] — index by cardId / id / card_id
            db = {}
            for c in raw:
                cid = getattr(c, "cardId", None)
                if cid is None:
                    cid = getattr(c, "card_id", None)
                if cid is None:
                    cid = getattr(c, "id", None)
                if cid is not None:
                    db[int(cid)] = c
            CARD_DB = db
    return CARD_DB


def _card_stage(card) -> str:
    """Synthesize stage/type string from Kaggle CardData boolean flags + cardType int."""
    if not card:
        return ""
    parts = []
    if getattr(card, 'megaEx', False):
        parts.append("Mega")
    if getattr(card, 'ex', False):
        parts.append("Ex")
    if getattr(card, 'stage2', False):
        parts.append("Stage2")
    elif getattr(card, 'stage1', False):
        parts.append("Stage1")
    elif getattr(card, 'basic', False):
        parts.append("Basic")
    ct = getattr(card, 'cardType', None)
    if isinstance(ct, int) and not parts:
        ct_map = {1: "Supporter", 2: "Item", 3: "Tool", 4: "Stadium", 5: "Energy"}
        ct_str = ct_map.get(ct)
        if ct_str:
            parts.append(ct_str)
    if not parts:
        for attr in ("stage", "card_type"):
            val = getattr(card, attr, None)
            if val and isinstance(val, str):
                return val
    return " ".join(parts)


def _select_options(select_obj: Any) -> List[Any]:
    """Defensively extract options list from Select object or dict (handles options vs option)."""
    if not select_obj:
        return []
    if isinstance(select_obj, dict):
        opts = select_obj.get("options", select_obj.get("option", [])) or []
        return list(opts) if isinstance(opts, (list, tuple)) else []
    for attr in ("options", "option"):
        val = getattr(select_obj, attr, None)
        if val is not None and isinstance(val, (list, tuple)):
            return list(val)
    return []


def _select_max_count(select_obj: Any) -> int:
    """Defensively extract max_count from Select object or dict (handles maxCount vs max_count)."""
    if not select_obj:
        return 1
    if isinstance(select_obj, dict):
        val = select_obj.get("maxCount", select_obj.get("max_count", 1))
        return int(val) if val is not None else 1
    for attr in ("maxCount", "max_count"):
        val = getattr(select_obj, attr, None)
        if val is not None:
            try:
                return int(val)
            except Exception:
                pass
    return 1


def _select_min_count(select_obj: Any) -> int:
    """Defensively extract min_count from Select object or dict (handles minCount vs min_count)."""
    if not select_obj:
        return 1
    if isinstance(select_obj, dict):
        val = select_obj.get("minCount", select_obj.get("min_count", 1))
        return int(val) if val is not None else 1
    for attr in ("minCount", "min_count"):
        val = getattr(select_obj, attr, None)
        if val is not None:
            try:
                return int(val)
            except Exception:
                pass
    return 1


def _opt_type(opt: Any) -> Any:
    """Defensively extract option type from Option object or dict (handles type vs option_type vs optionType)."""
    if not opt:
        return None
    if isinstance(opt, dict):
        return opt.get("type", opt.get("option_type", opt.get("optionType")))
    for attr in ("option_type", "optionType", "type"):
        val = getattr(opt, attr, None)
        if val is not None:
            return val
    return None


def _wrap_obs(obs):
    """Adapt Kaggle Observation (obs.current.players[]) to the flat format our engine expects."""
    if not obs:
        return obs

    # Normalize select object so options, max_count, min_count are always present
    raw_sel = getattr(obs, 'select', None)
    wrapped_sel = None
    if raw_sel:
        opts = _select_options(raw_sel)
        max_c = _select_max_count(raw_sel)
        min_c = _select_min_count(raw_sel)
        ctx = getattr(raw_sel, 'context', None)
        if isinstance(raw_sel, dict):
            ctx = raw_sel.get('context')
        wrapped_sel = SimpleNamespace(
            options=opts,
            option=opts,
            max_count=max_c,
            maxCount=max_c,
            min_count=min_c,
            minCount=min_c,
            context=ctx,
        )

    if hasattr(obs, 'my_active'):
        if wrapped_sel:
            obs.select = wrapped_sel
        return obs

    state = getattr(obs, 'current', None)
    if not state or not hasattr(state, 'players') or len(state.players) < 2:
        if wrapped_sel:
            obs.select = wrapped_sel
        return obs

    yi = getattr(state, 'yourIndex', 0)
    my_ps = state.players[yi]
    opp_ps = state.players[1 - yi]

    def _wrap_pkmn(p):
        return SimpleNamespace(
            id=getattr(p, 'id', 0), serial=getattr(p, 'serial', 0),
            hp=getattr(p, 'hp', 0),
            max_hp=getattr(p, 'maxHp', getattr(p, 'max_hp', 0)),
            energies=getattr(p, 'energies', []),
            energy_cards=getattr(p, 'energyCards', getattr(p, 'energy_cards', [])),
        )

    my_active = [_wrap_pkmn(p) for p in getattr(my_ps, 'active', [])]
    opp_active = [_wrap_pkmn(p) for p in getattr(opp_ps, 'active', [])]
    my_bench = [_wrap_pkmn(p) for p in getattr(my_ps, 'bench', [])]
    opp_bench = [_wrap_pkmn(p) for p in getattr(opp_ps, 'bench', [])]

    return SimpleNamespace(
        select=wrapped_sel,
        current=state,
        my_state=SimpleNamespace(
            bench_max=getattr(my_ps, 'benchMax', getattr(my_ps, 'bench_max', 5)),
            deck_count=getattr(my_ps, 'deckCount', getattr(my_ps, 'deck_count', 0)),
            hand_count=getattr(my_ps, 'handCount', getattr(my_ps, 'hand_count', 0)),
            prize_count=len(getattr(my_ps, 'prize', [])),
            active=my_active, bench=my_bench,
            hand=getattr(my_ps, 'hand', []),
        ),
        opp_state=SimpleNamespace(
            prize_count=len(getattr(opp_ps, 'prize', [])),
            active=opp_active, bench=opp_bench,
        ),
        my_active=my_active, opp_active=opp_active,
        my_bench=my_bench, opp_bench=opp_bench,
        my_hand=getattr(my_ps, 'hand', []),
        my_prize_count=len(getattr(my_ps, 'prize', [])),
        opp_prize_count=len(getattr(opp_ps, 'prize', [])),
    )


def is_riolu_card(card: Optional[Card]) -> bool:
    if not card or not card.name:
        return False
    return card.name.strip().lower() == "riolu"


def is_riolu_id(cid: Optional[int]) -> bool:
    if cid is None:
        return False
    db = get_card_db()
    card = db.get(cid)
    return is_riolu_card(card)


def is_mega_lucario_ex_card(card: Optional[Card]) -> bool:
    if not card:
        return False
    name = getattr(card, 'name', '') or ''
    if getattr(card, 'megaEx', False) and 'lucario' in name.lower():
        return True
    name_clean = name.strip().lower()
    stage_clean = _card_stage(card).strip().lower()
    return "mega lucario" in name_clean or ("lucario" in name_clean and "mega" in stage_clean)


def is_mega_lucario_ex_id(cid: Optional[int]) -> bool:
    if cid is None:
        return False
    db = get_card_db()
    card = db.get(cid)
    return is_mega_lucario_ex_card(card)


def get_prize_value(card: Optional[Card]) -> int:
    if not card:
        return 1
    if getattr(card, 'megaEx', False):
        return 3
    name_lower = (getattr(card, 'name', '') or '').lower()
    if getattr(card, 'ex', False) or ' ex' in name_lower or name_lower.endswith('ex'):
        return 2
    if 'vmax' in name_lower or 'vstar' in name_lower:
        return 2
    return 1


def get_fallback_energy_card_id() -> int:
    return 6


def _opt_index(opt: Any, fallback: int = 0) -> int:
    """Safely extract option index from typed Option or dict."""
    if hasattr(opt, "index") and opt.index is not None:
        return opt.index
    if isinstance(opt, dict) and "index" in opt and opt["index"] is not None:
        try:
            return int(opt["index"])
        except Exception:
            pass
    return fallback


def resolve_card_id(opt: Option, obs: Observation) -> Optional[int]:
    """
    Resolve card ID for an option safely across typed and dict structures.
    CARD, TOOL_CARD, ENERGY_CARD carry card_id directly on wire.
    PLAY / EVOLVE carry hand or bench position in index / in_play_index.
    """
    cid = getattr(opt, "card_id", None)
    if cid is None and isinstance(opt, dict):
        cid = opt.get("card_id")
    if cid is not None:
        return cid

    opt_type = getattr(opt, "option_type", None)
    if opt_type is None and isinstance(opt, dict):
        opt_type = opt.get("type")

    opt_type_str = str(getattr(opt_type, "name", opt_type)).upper()

    hand = getattr(obs, "my_hand", []) or []
    bench = getattr(obs, "my_bench", []) or []

    in_play_idx = getattr(opt, "in_play_index", None)
    if in_play_idx is None and isinstance(opt, dict):
        in_play_idx = opt.get("in_play_index") if "in_play_index" in opt else opt.get("inPlayIndex")

    if in_play_idx is not None:
        in_play_area = getattr(opt, "in_play_area", None)
        if in_play_area is None and isinstance(opt, dict):
            in_play_area = opt.get("in_play_area") if "in_play_area" in opt else opt.get("inPlayArea")
        in_play_area_str = str(getattr(in_play_area, "name", in_play_area)).upper() if in_play_area is not None else ""

        if in_play_area_str in ("BENCH", "5") or "BENCH" in in_play_area_str:
            if 0 <= in_play_idx < len(bench):
                b_item = bench[in_play_idx]
                return getattr(b_item, "id", b_item)
            return None
        else:
            if 0 <= in_play_idx < len(hand):
                h_item = hand[in_play_idx]
                return getattr(h_item, "id", h_item) if hasattr(h_item, "id") else h_item
            return None

    if opt_type_str in ("PLAY", "EVOLVE", "7", "8") or opt_type in (OptionType.PLAY, OptionType.EVOLVE):
        opt_idx = getattr(opt, "index", None)
        if opt_idx is None and isinstance(opt, dict):
            opt_idx = opt.get("index")

        if opt_idx is not None:
            if 0 <= opt_idx < len(hand):
                h_item = hand[opt_idx]
                return getattr(h_item, "id", h_item) if hasattr(h_item, "id") else h_item
            return None


    return None


@dataclass
class AttackPlan:
    my_active_card: Optional[Card] = None
    opp_active_card: Optional[Card] = None
    opp_active_hp: int = 999
    best_attack_idx: Optional[int] = None
    best_attack_damage: int = 0
    is_ko: bool = False
    is_game_winning_ko: bool = False
    target_prize_value: int = 1


def compute_effective_damage(attack, attacker_card, defender_card) -> int:
    """Compute effective damage. Handles both Attack objects and int attack IDs."""
    if not attack:
        return 0

    # Kaggle: attacks are integer IDs, not objects with .damage
    if isinstance(attack, int):
        # Estimate damage based on the attacker card's stage
        if attacker_card:
            if getattr(attacker_card, 'megaEx', False):
                base_dmg = 120
            elif getattr(attacker_card, 'ex', False):
                base_dmg = 80
            elif getattr(attacker_card, 'stage1', False):
                base_dmg = 60
            elif getattr(attacker_card, 'stage2', False):
                base_dmg = 100
            else:
                base_dmg = 30
        else:
            base_dmg = 30
    else:
        base_dmg = getattr(attack, 'damage', 0)

    if base_dmg <= 0 or not defender_card:
        return max(0, base_dmg)

    # Weakness: double damage if type matches
    weakness = getattr(defender_card, 'weakness', None)
    if weakness:
        w_str = str(weakness).upper()
        atk_type = str(getattr(attacker_card, 'energyType', getattr(attacker_card, 'element_type', ''))).upper()
        if atk_type and atk_type in w_str:
            base_dmg *= 2

    # Resistance: reduce damage
    resistance = getattr(defender_card, 'resistance', None)
    if resistance:
        r_str = str(resistance)
        matches = re.findall(r"-\d+", r_str)
        if matches:
            base_dmg = max(0, base_dmg - abs(int(matches[0])))
        else:
            base_dmg = max(0, base_dmg - 20)

    return base_dmg


def compute_attack_plan(obs: Observation) -> AttackPlan:
    plan = AttackPlan()
    db = get_card_db()

    my_active = obs.my_active[0] if obs.my_active else None
    opp_active = obs.opp_active[0] if obs.opp_active else None

    if not my_active or not opp_active:
        return plan

    plan.my_active_card = db.get(my_active.id)
    plan.opp_active_card = db.get(opp_active.id)
    plan.opp_active_hp = opp_active.hp

    # Prize-aware target scoring: 3 for Mega ex, 2 for ex, 1 for basic
    if plan.opp_active_card:
        plan.target_prize_value = get_prize_value(plan.opp_active_card)
    else:
        plan.target_prize_value = 1

    # Evaluate best attack damage
    if plan.my_active_card and plan.my_active_card.attacks:
        best_dmg = -1
        best_i = None
        for i, atk in enumerate(plan.my_active_card.attacks):
            dmg = compute_effective_damage(atk, plan.my_active_card, plan.opp_active_card)
            if dmg > best_dmg:
                best_dmg = dmg
                best_i = i
        plan.best_attack_damage = max(0, best_dmg)
        plan.best_attack_idx = best_i

    plan.is_ko = plan.best_attack_damage >= plan.opp_active_hp
    prizes_needed = obs.my_prize_count if obs.my_prize_count is not None else 6
    if plan.is_ko:
        if prizes_needed <= 0 or obs.my_prize_count == 0 or plan.target_prize_value >= prizes_needed or len(obs.opp_bench) == 0:
            plan.is_game_winning_ko = True
        else:
            plan.is_game_winning_ko = False
    else:
        plan.is_game_winning_ko = False

    return plan


def score_option(opt: Option, obs: Observation, plan: AttackPlan) -> int:
    db = get_card_db()
    opt_type = opt.option_type
    opt_type_str = str(opt_type.name if hasattr(opt_type, "name") else opt_type)
    ctx = obs.select.context if obs.select else None
    ctx_str = str(ctx.name if hasattr(ctx, "name") else ctx)

    # Prize bonus calculation: +3,000 for 3-prize Mega ex, +2,000 for 2-prize ex, +1,000 for Basic
    prize_bonus = 3000 if plan.target_prize_value == 3 else (2000 if plan.target_prize_value == 2 else 1000)

    # 1. Non-MAIN contexts (Setup / Switch / Search / Forced / Discard)
    if ctx_str in ("SETUP_ACTIVE_POKEMON", "SETUP_BENCH_POKEMON"):
        cid = resolve_card_id(opt, obs)
        if is_riolu_id(cid):
            return 9000
        elif cid:
            c = db.get(cid)
            if c and c.hp >= 100:
                return 7000
        return 5000 - _opt_index(opt)

    if ctx_str in ("SWITCH", "TO_ACTIVE"):
        idx = opt.in_play_index if opt.in_play_index is not None else opt.index
        if idx is not None and 0 <= idx < len(obs.my_bench):
            b_pkmn = obs.my_bench[idx]
            return 8000 + getattr(b_pkmn, "hp", 0)
        return 5000 - _opt_index(opt)

    if ctx_str in ("IS_FIRST", "MULLIGAN"):
        if opt_type_str == "YES" or opt_type == OptionType.YES:
            return 9000
        return 1000

    if ctx_str in ("DISCARD", "DISCARD_ENERGY_CARD", "DISCARD_TOOL_CARD", "DISCARD_CARD_OR_ATTACHED_CARD", "DISCARD_ENERGY") and opt_type_str in ("DISCARD", "11"):
        cid = resolve_card_id(opt, obs)
        if cid:
            if is_mega_lucario_ex_id(cid):
                return -1000
            if is_riolu_id(cid):
                return 1000
            c = db.get(cid)
            if c:
                stage = _card_stage(c).lower()
                if "supporter" in stage:
                    return 2000
                if "energy" in stage:
                    return 7000
                if "basic" in stage:
                    return 6000
        return 5000 - _opt_index(opt)

    if ctx_str in ("TO_HAND", "TO_BENCH", "TO_FIELD"):
        cid = resolve_card_id(opt, obs)
        if cid:
            if is_mega_lucario_ex_id(cid):
                return 9000
            if is_riolu_id(cid):
                return 8500
            c = db.get(cid)
            if c:
                stage = _card_stage(c).lower()
                if "supporter" in stage:
                    return 8000
                if "item" in stage:
                    return 7000
        return 6000 - _opt_index(opt)

    if ctx_str in ("ATTACH_FROM", "ATTACH_TO"):
        if opt.in_play_area == AreaType.ACTIVE or str(opt.in_play_area) in ("ACTIVE", "4"):
            return 8000
        return 6000

    if ctx_str in ("EVOLVES_TO", "EVOLVES_FROM"):
        cid = resolve_card_id(opt, obs)
        if is_mega_lucario_ex_id(cid):
            return 9000
        return 7000

    # CARD / NUMBER / TOOL_CARD / ENERGY_CARD selection
    if opt_type_str in ("CARD", "TOOL_CARD", "ENERGY_CARD", "ENERGY", "NUMBER", "3", "4", "5", "6") or opt_type in (OptionType.CARD, OptionType.TOOL_CARD, OptionType.ENERGY_CARD, OptionType.ENERGY, OptionType.NUMBER):
        cid = resolve_card_id(opt, obs)
        if cid:
            c = db.get(cid)
            if c:
                if is_mega_lucario_ex_id(cid):
                    return 8000
                if is_riolu_id(cid):
                    return 7000
                if "Supporter" in _card_stage(c):
                    return 6000
                if "Energy" in _card_stage(c):
                    return 5000
        return 3000 - _opt_index(opt)

    # 2. MAIN context decisions

    # ATTACK
    if opt_type_str == "ATTACK" or opt_type == OptionType.ATTACK:
        # Game-winning KO check -> 50,000 (highest priority score)
        if plan.is_game_winning_ko:
            return 50000
        if plan.is_ko:
            return 10000 + prize_bonus
        return 8500 + prize_bonus + min(plan.best_attack_damage, 1000)

    # EVOLVE (Riolu -> Mega Lucario ex evolution priority: +8,000 active / +7,000 bench)
    if opt_type_str == "EVOLVE" or opt_type == OptionType.EVOLVE:
        cid = resolve_card_id(opt, obs)
        if is_mega_lucario_ex_id(cid):
            if opt.in_play_area == AreaType.ACTIVE or str(opt.in_play_area) in ("ACTIVE", "4"):
                return 8000
            return 7000
        return 6000

    # PLAY (Supporter 6,500 > Search Item 5,500 > Basic 3,500)
    if opt_type_str == "PLAY" or opt_type == OptionType.PLAY:
        cid = resolve_card_id(opt, obs)
        if cid:
            c = db.get(cid)
            if c:
                stage = _card_stage(c).lower()
                if "supporter" in stage:
                    return 6500
                if "item" in stage or "tool" in stage:
                    return 5500
                max_bench = getattr(obs.my_state, 'bench_max', 5) if obs.my_state and getattr(obs.my_state, 'bench_max', 0) > 0 else 5
                if "basic" in stage and len(obs.my_bench) < max_bench:
                    return 3500
        return 2000

    # ATTACH (Active energy deficit = 1 gets +5,000 active / +4,500 bench)
    if opt_type_str == "ATTACH" or opt_type == OptionType.ATTACH:
        is_active = opt.in_play_area == AreaType.ACTIVE or str(opt.in_play_area) in ("ACTIVE", "4")
        if is_active:
            my_act = obs.my_active[0] if obs.my_active else None
            my_act_card = plan.my_active_card
            if my_act and my_act_card and my_act_card.attacks:
                curr = len(my_act.energies)
                deficits = [atk.energy_count - curr for atk in my_act_card.attacks if hasattr(atk, 'energy_count')]
                if any(d == 1 for d in deficits):
                    return 5000  # Energy deficit = 1 active
            return 4000
        else:
            return 4500 if len(obs.my_bench) > 0 else 3000  # Bench attachment

    # ABILITY
    if opt_type_str == "ABILITY" or opt_type == OptionType.ABILITY:
        return 4000

    # RETREAT (Bench-aware retreat: +4,200 only if active HP < 40% and healthy bench attacker ready; -1,000 if unsafe)
    if opt_type_str == "RETREAT" or opt_type == OptionType.RETREAT:
        my_act = obs.my_active[0] if obs.my_active else None
        my_card = plan.my_active_card
        if my_act and my_card and my_card.hp > 0:
            hp_ratio = my_act.hp / float(my_card.hp)
            has_bench_ready = any(b.hp >= 80 for b in obs.my_bench)
            if hp_ratio < 0.4 and has_bench_ready:
                return 4200
        return -1000

    # YES / NO
    if opt_type_str == "YES" or opt_type == OptionType.YES:
        return 5000
    if opt_type_str == "NO" or opt_type == OptionType.NO:
        return 1000

    # END turn
    if opt_type_str == "END" or opt_type == OptionType.END:
        return 100

    # Default fallback
    return 1000 - _opt_index(opt)


# =============================================================================
# PATCH 5: MACRO-INTENTS (Options Framework) + DECISION ENTROPY
# Sutton, Precup & Singh 1999 — relabels score_option() buckets into named
# intents with initiation conditions. Zero compute cost; pure report value.
# =============================================================================

MACRO_INTENTS = {
    "LETHAL":    {"initiation": "KO wins game",                        "scores": (50000, 50000)},
    "AGGRO_KO":  {"initiation": "KO is feasible",                      "scores": (10000, 13999)},
    "SETUP":     {"initiation": "setup context (active/bench select)",  "scores": (9000, 9000)},
    "ATTACK":    {"initiation": "no better option, attack available",   "scores": (8500, 9999)},
    "DEVELOP":   {"initiation": "bench < 3 or evolution available",     "scores": (7000, 8499)},
    "RESOURCE":  {"initiation": "supporter/item in hand",              "scores": (5500, 6999)},
    "STABILIZE": {"initiation": "HP < 40% and healthy bench ready",    "scores": (4200, 4200)},
    "POWER_UP":  {"initiation": "energy deficit on attacker",          "scores": (4000, 5499)},
    "PASS":      {"initiation": "nothing useful",                      "scores": (0, 999)},
}


def macro_intent_for_score(score: int) -> str:
    """Map a score_option() output to its named macro-intent."""
    for name, spec in MACRO_INTENTS.items():
        lo, hi = spec["scores"]
        if lo <= score <= hi:
            return name
    return "UNKNOWN"


def decision_entropy(scores: List[int], temperature: float = 1000.0) -> float:
    """H = -Σ p_i log p_i over softmax-normalized scores.
    Cheap per-turn 'how contested was this decision' signal for the
    Strategy report's explainability section."""
    if not scores or len(scores) <= 1:
        return 0.0
    s = np.array(scores, dtype=np.float64)
    s = s - np.max(s)  # numerical stability
    exp_s = np.exp(s / temperature)
    sum_exp = np.sum(exp_s)
    if sum_exp <= 0 or np.isnan(sum_exp):
        return 0.0
    p = exp_s / sum_exp
    p = p[p > 1e-12]
    res = float(-np.sum(p * np.log(p)))
    if math.isnan(res) or math.isinf(res):
        return 0.0
    return res


# =============================================================================
# NEURAL SCAFFOLDING (Preserved & Inert during Rule Decisions)
# =============================================================================

class StateEncoder:
    """
    Encodes Observation into an 84-dimensional feature vector.
    Currently returns np.zeros(84, dtype=np.float32).
    """

    def encode(self, obs: Observation) -> np.ndarray:
        return np.zeros(84, dtype=np.float32)


class NeuralWorker:
    """
    Pure NumPy MLP for state value estimation.
    Architecture: 84 -> 64 (ReLU) -> 32 (ReLU) -> 1 (Sigmoid).
    """

    def __init__(self):
        self.encoder = StateEncoder()
        rng = np.random.RandomState(42)
        self.w1 = rng.randn(84, 64).astype(np.float32) * 0.1
        self.b1 = np.zeros(64, dtype=np.float32)
        self.w2 = rng.randn(64, 32).astype(np.float32) * 0.1
        self.b2 = np.zeros(32, dtype=np.float32)
        self.w3 = rng.randn(32, 1).astype(np.float32) * 0.1
        self.b3 = np.zeros(1, dtype=np.float32)

    def score_state(self, obs: Observation) -> float:
        x = self.encoder.encode(obs)
        x = np.maximum(0, np.dot(x, self.w1) + self.b1)
        x = np.maximum(0, np.dot(x, self.w2) + self.b2)
        out = np.dot(x, self.w3) + self.b3
        return float(1.0 / (1.0 + math.exp(-float(out[0]))))


class GameLogger:
    """Logs (observation_raw, action_indices) pairs for offline training."""

    def __init__(self, path="game_log.jsonl"):
        self._f = None
        try:
            self._f = open(path, "a", encoding="utf-8")
        except Exception:
            pass

    def log(self, obs_raw, action_indices, entropy=None, intent=None):
        if not self._f:
            return
        try:
            record = {"o": obs_raw, "a": action_indices}
            if entropy is not None:
                record["entropy"] = round(entropy, 4)
            if intent is not None:
                record["intent"] = intent
            self._f.write(json.dumps(record) + "\n")
            self._f.flush()
        except Exception:
            pass


# =============================================================================
# HEURISTIC ENGINE
# =============================================================================

class HeuristicEngine:
    def __init__(self, deck_path: str = "deck.csv"):
        self.deck_path = deck_path
        self.deck = self._load_deck(deck_path)
        get_card_db()
        self.neural_worker = NeuralWorker()

    def _load_deck(self, path: str) -> List[int]:
        d = []
        base_dir = os.path.dirname(os.path.abspath(__file__))
        search_paths = [
            path,
            os.path.join(base_dir, path),
            "/kaggle/input/pokemon-tcg-ai-battle/deck.csv",
            "/kaggle/input/competitions/pokemon-tcg-ai-battle/deck.csv",
            "/kaggle/input/pokemon-tcg-ai-battle-challenge-strategy/deck.csv",
            "/kaggle/input/competitions/pokemon-tcg-ai-battle-challenge-strategy/deck.csv",
        ]
        resolved = next((p for p in search_paths if p and os.path.exists(p)), None)
        if resolved:
            try:
                with open(resolved, "r", encoding="utf-8") as f:
                    d = [int(l.strip()) for l in f if l.strip().isdigit()]
            except Exception:
                pass

        if len(d) != 60:
            fallback_id = get_fallback_energy_card_id()
            d = (d + [fallback_id] * 60)[:60]
        return d

    def get_deck(self) -> List[int]:
        return self.deck

    def choose(self, obs: Observation) -> List[int]:
        obs = _wrap_obs(obs)
        if not obs.select or not obs.select.options:
            return []

        options = obs.select.options
        if len(options) == 1:
            return [0]

        plan = compute_attack_plan(obs)

        # Score every legal option by its 0-based list position
        scored_opts = []
        for list_idx, opt in enumerate(options):
            score = score_option(opt, obs, plan)
            scored_opts.append((score, list_idx))

        # Sort options descending by integer score
        scored_opts.sort(key=lambda x: x[0], reverse=True)

        max_c = obs.select.max_count if obs.select.max_count > 0 else 1
        min_c = obs.select.min_count if obs.select.min_count > 0 else 1
        target_count = max(max_c, min_c)

        top_indices = [list_idx for score, list_idx in scored_opts[:target_count]]

        # Ensure we return at least min_count options if available
        if len(top_indices) < min_c and len(options) >= min_c:
            for list_idx in range(len(options)):
                if list_idx not in top_indices:
                    top_indices.append(list_idx)
                    if len(top_indices) >= min_c:
                        break

        return top_indices


# =============================================================================
# AGENT ENTRY POINT
# =============================================================================

_engine = None
_logger = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = HeuristicEngine("deck.csv")
    return _engine


def _get_logger():
    global _logger
    if _logger is None:
        _logger = GameLogger("game_log.jsonl")
    return _logger


def action(obs: Observation) -> List[int]:
    """Action ranking entry point accepting typed Observation or raw dict."""
    if isinstance(obs, dict):
        parsed = to_observation_class(obs)
    else:
        parsed = obs

    if parsed.select is None:
        return _get_engine().get_deck()

    return _get_engine().choose(parsed)


def agent(observation: Any, configuration: Any = None) -> List[int]:
    """Kaggle environment entry point."""
    try:
        obs = to_observation_class(observation)
        obs = _wrap_obs(obs)
        if obs.select is None:
            return _get_engine().get_deck()

        actions = _get_engine().choose(obs)

        # Patch 5: log entropy + macro-intent alongside action indices
        try:
            entropy_val = None
            intent_val = None
            if obs.select and obs.select.options:
                plan = compute_attack_plan(obs)
                scores = [score_option(opt, obs, plan) for opt in obs.select.options]
                entropy_val = decision_entropy(scores)
                if actions:
                    # Intent of the chosen action (highest-scored option)
                    top_score = max(scores)
                    intent_val = macro_intent_for_score(top_score)
            _get_logger().log(observation, actions, entropy=entropy_val, intent=intent_val)
        except Exception:
            pass
        return actions if actions else [0]
    except Exception as e:
        logger.error(f"Agent error: {e}")
        try:
            is_setup = False
            if isinstance(observation, dict):
                is_setup = observation.get("select") is None
            elif hasattr(observation, "select"):
                is_setup = observation.select is None or getattr(observation, "is_setup_phase", False)
            
            if is_setup:
                return _get_engine().get_deck()
            
            return [0]
        except Exception:
            try:
                return _get_engine().get_deck()
            except Exception:
                return [0]
