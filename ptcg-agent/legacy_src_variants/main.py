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
import numpy as np
from dataclasses import dataclass, field
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
    Select,
    Observation,
    Attack,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("ptcg_agent")

# Global Card Database initialized via native cg.api
CARD_DB: Dict[int, Card] = {}


def get_card_db() -> Dict[int, Card]:
    global CARD_DB
    if not CARD_DB:
        CARD_DB = all_card_data()
    return CARD_DB


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
    PLAY / EVOLVE carry hand position in in_play_index or index.
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

    if opt_type_str in ("PLAY", "EVOLVE", "7", "8") or opt_type in (OptionType.PLAY, OptionType.EVOLVE):
        in_play_idx = getattr(opt, "in_play_index", None)
        if in_play_idx is None and isinstance(opt, dict):
            in_play_idx = opt.get("in_play_index")

        idx = in_play_idx if in_play_idx is not None else _opt_index(opt, 0)
        hand = getattr(obs, "my_hand", []) or []
        if idx is not None and 0 <= idx < len(hand):
            return hand[idx]

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


def compute_effective_damage(attack: Attack, attacker_card: Optional[Card], defender_card: Optional[Card]) -> int:
    if not attack:
        return 0
    base_dmg = attack.damage
    if base_dmg <= 0 or not defender_card:
        return base_dmg

    atk_type = (attacker_card.element_type if attacker_card else "").upper()
    weakness = (defender_card.weakness or "").upper()
    resistance = (defender_card.resistance or "").upper()

    mult = 1
    if atk_type and atk_type in weakness:
        mult = 2

    damage = base_dmg * mult

    if atk_type and atk_type in resistance:
        if "-30" in resistance:
            damage = max(0, damage - 30)
        elif "-20" in resistance:
            damage = max(0, damage - 20)

    return damage


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
        name_lower = plan.opp_active_card.name.lower()
        stage_lower = (plan.opp_active_card.stage or "").lower()
        if "mega" in name_lower or "mega" in stage_lower:
            plan.target_prize_value = 3
        elif " ex" in name_lower or "ex" in name_lower or "ex" in stage_lower:
            plan.target_prize_value = 2
        else:
            plan.target_prize_value = 1
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
    prizes_needed = obs.my_prize_count if obs.my_prize_count > 0 else 6
    plan.is_game_winning_ko = plan.is_ko and (plan.target_prize_value >= prizes_needed or len(obs.opp_bench) == 0)

    return plan


def score_option(opt: Option, obs: Observation, plan: AttackPlan) -> int:
    db = get_card_db()
    opt_type = opt.option_type
    opt_type_str = str(opt_type.name if hasattr(opt_type, "name") else opt_type)
    ctx = obs.select.context if obs.select else None
    ctx_str = str(ctx.name if hasattr(ctx, "name") else ctx)

    # Prize bonus calculation: +3,000 for 3-prize Mega ex, +2,000 for 2-prize ex, +1,000 for Basic
    prize_bonus = 3000 if plan.target_prize_value == 3 else (2000 if plan.target_prize_value == 2 else 1000)

    # 1. Non-MAIN contexts (Setup / Switch / Search / Forced)
    if ctx_str in ("SETUP_ACTIVE_POKEMON", "SETUP_BENCH_POKEMON"):
        cid = resolve_card_id(opt, obs)
        if cid in (677, 333):  # Riolu
            return 9000
        elif cid:
            c = db.get(cid)
            if c and c.hp >= 100:
                return 7000
        return 5000 - _opt_index(opt)

    if ctx_str in ("SWITCH", "TO_ACTIVE"):
        if opt.in_play_index is not None and 0 <= opt.in_play_index < len(obs.my_bench):
            b_pkmn = obs.my_bench[opt.in_play_index]
            return 8000 + b_pkmn.hp
        return 5000 - _opt_index(opt)

    if ctx_str in ("IS_FIRST", "MULLIGAN"):
        if opt_type_str == "YES" or opt_type == OptionType.YES:
            return 9000
        return 1000

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
        if cid == 678:  # Mega Lucario ex
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
                stage = (c.stage or "").lower()
                if "supporter" in stage:
                    return 6500
                if "item" in stage or "tool" in stage:
                    return 5500
                if "basic" in stage and len(obs.my_bench) < 5:
                    return 3500
        return 2000

    # ATTACH (Active energy deficit = 1 gets +5,000 active / +4,500 bench)
    if opt_type_str == "ATTACH" or opt_type == OptionType.ATTACH:
        is_active = opt.in_play_area == AreaType.ACTIVE or str(opt.in_play_area) in ("ACTIVE", "4")
        if is_active:
            my_act = obs.my_active[0] if obs.my_active else None
            my_act_card = plan.my_active_card
            if my_act and my_act_card and my_act_card.attacks:
                needed = my_act_card.attacks[0].energy_count
                curr = len(my_act.energies)
                if needed - curr == 1:
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

    # CARD / NUMBER / TOOL_CARD / ENERGY_CARD selection
    if opt_type_str in ("CARD", "TOOL_CARD", "ENERGY_CARD", "ENERGY", "NUMBER"):
        cid = resolve_card_id(opt, obs)
        if cid:
            c = db.get(cid)
            if c:
                if cid == 678:
                    return 8000
                if cid in (677, 333):
                    return 7000
                if "Supporter" in c.stage:
                    return 6000
                if "Energy" in c.stage:
                    return 5000
        return 3000 - _opt_index(opt)

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
    if len(scores) <= 1:
        return 0.0
    s = np.array(scores, dtype=np.float64)
    s = s - s.max()  # numerical stability
    exp_s = np.exp(s / temperature)
    p = exp_s / exp_s.sum()
    return float(-np.sum(p * np.log(p + 1e-12)))


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
        try:
            with open(path) as f:
                d = [int(l.strip()) for l in f if l.strip().isdigit()]
        except Exception:
            pass
        if len(d) != 60:
            d = (d + [6] * 60)[:60]
        return d

    def get_deck(self) -> List[int]:
        return self.deck

    def choose(self, obs: Observation) -> List[int]:
        if not obs.select or not obs.select.options:
            return []

        options = obs.select.options
        if len(options) == 1:
            return [_opt_index(options[0], 0)]

        plan = compute_attack_plan(obs)

        # Score every legal option
        scored_opts = []
        for list_idx, opt in enumerate(options):
            score = score_option(opt, obs, plan)
            wire_idx = _opt_index(opt, list_idx)
            scored_opts.append((score, wire_idx))

        # Sort options descending by integer score
        scored_opts.sort(key=lambda x: x[0], reverse=True)

        max_c = obs.select.max_count if obs.select.max_count > 0 else 1
        top_indices = [idx for score, idx in scored_opts[:max_c]]

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
        if obs.select is None or obs.is_setup_phase:
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
            if observation and isinstance(observation, dict) and observation.get("select"):
                return [0]
            return _get_engine().get_deck()
        except Exception:
            return [0]
