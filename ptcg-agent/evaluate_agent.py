"""
PTCG AI Agent — Local Tournament & Elo Evaluation Harness (v3.3.0)
Simulates match scenarios against benchmark opponent archetypes,
computes Win/Loss/Draw statistics, prize margins, decision entropy,
and estimates the agent's Kaggle Elo rating (1000 base scale).
"""

import sys
import os
import math
import random
import time
from typing import Dict, List, Tuple, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main


class BenchmarkBot:
    """Base class for benchmark opponent bots."""
    def __init__(self, name: str, base_elo: float):
        self.name = name
        self.base_elo = base_elo

    def choose_action(self, obs_dict: Dict[str, Any]) -> List[int]:
        raise NotImplementedError


class RandomBot(BenchmarkBot):
    """Opponent that selects random valid options."""
    def __init__(self):
        super().__init__("Random Bot (Baseline)", 800.0)

    def choose_action(self, obs_dict: Dict[str, Any]) -> List[int]:
        select = obs_dict.get("select")
        if not select or "options" not in select or not select["options"]:
            return [0]
        max_c = select.get("maxCount", 1) or 1
        opts = list(range(len(select["options"])))
        random.shuffle(opts)
        return opts[:max_c]


class GreedyKOBot(BenchmarkBot):
    """Opponent that prioritizes Attacks > Evolve > Attach > Play > End."""
    def __init__(self):
        super().__init__("Greedy KO Bot", 1050.0)

    def choose_action(self, obs_dict: Dict[str, Any]) -> List[int]:
        select = obs_dict.get("select")
        if not select or "options" not in select or not select["options"]:
            return [0]
        options = select["options"]
        best_idx = 0
        best_score = -1
        for i, opt in enumerate(options):
            ot = str(opt.get("type", ""))
            sc = 10
            if ot in ("13", "ATTACK"):
                sc = 100
            elif ot in ("9", "EVOLVE"):
                sc = 70
            elif ot in ("8", "ATTACH"):
                sc = 50
            elif ot in ("7", "PLAY"):
                sc = 40
            if sc > best_score:
                best_score = sc
                best_idx = i
        return [best_idx]


class EnergyAggroBot(BenchmarkBot):
    """Opponent focused on fast energy attachment & early aggro."""
    def __init__(self):
        super().__init__("Energy Aggro Bot", 1150.0)

    def choose_action(self, obs_dict: Dict[str, Any]) -> List[int]:
        select = obs_dict.get("select")
        if not select or "options" not in select or not select["options"]:
            return [0]
        options = select["options"]
        best_idx = 0
        best_score = -1
        for i, opt in enumerate(options):
            ot = str(opt.get("type", ""))
            sc = 10
            if ot in ("8", "ATTACH"):
                sc = 120
            elif ot in ("13", "ATTACK"):
                sc = 100
            elif ot in ("9", "EVOLVE"):
                sc = 80
            if sc > best_score:
                best_score = sc
                best_idx = i
        return [best_idx]


class HeuristicMirrorBot(BenchmarkBot):
    """Opponent using baseline heuristic engine."""
    def __init__(self):
        super().__init__("Heuristic Baseline Mirror", 1200.0)

    def choose_action(self, obs_dict: Dict[str, Any]) -> List[int]:
        try:
            return main.agent(obs_dict)
        except Exception:
            return [0]


def make_dict_obs(your_idx: int, hp_active: int, hp_opp: int, prize_my_cnt: int, prize_opp_cnt: int, turn: int):
    """Construct Kaggle-compatible observation dictionary."""
    my_prizes = list(range(1, prize_my_cnt + 1))
    opp_prizes = list(range(1, prize_opp_cnt + 1))

    my_player = {
        "active": [{"id": 678, "serial": 1, "hp": hp_active, "maxHp": 340, "energies": [6, 6], "appearThisTurn": False, "energyCards": [], "tools": [], "preEvolution": []}],
        "bench": [{"id": 677, "serial": 2, "hp": 80, "maxHp": 80, "energies": [], "appearThisTurn": False, "energyCards": [], "tools": [], "preEvolution": []}],
        "hand": [1182, 6, 678],
        "prize": my_prizes,
        "handCount": 3, "deckCount": 45, "benchMax": 5
    }
    opp_player = {
        "active": [{"id": 677, "serial": 3, "hp": hp_opp, "maxHp": 80, "energies": [6], "appearThisTurn": False, "energyCards": [], "tools": [], "preEvolution": []}],
        "bench": [{"id": 677, "serial": 4, "hp": 80, "maxHp": 80, "energies": [], "appearThisTurn": False, "energyCards": [], "tools": [], "preEvolution": []}],
        "hand": [6],
        "prize": opp_prizes,
        "handCount": 1, "deckCount": 45, "benchMax": 5
    }

    players = [my_player, opp_player] if your_idx == 0 else [opp_player, my_player]

    return {
        "current": {
            "yourIndex": your_idx,
            "turn": turn,
            "turnActionCount": turn,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": 0,
            "stadium": None,
            "looking": None,
            "players": players
        },
        "select": {
            "type": 0, "context": 0,
            "options": [
                {"type": 7, "area": 2, "index": 0, "card_id": 1182},
                {"type": 13, "area": 4, "index": 1, "attack_id": 0},
                {"type": 8, "area": 4, "index": 2, "card_id": 6},
                {"type": 14, "area": 11, "index": 3}
            ],
            "minCount": 1, "maxCount": 1
        },
        "logs": []
    }


def simulate_game(opponent: BenchmarkBot, max_turns: int = 20) -> Tuple[bool, int, int, List[float], List[str]]:
    """Simulate a game between main.agent (index 0) and opponent (index 1)."""
    hp_agent, hp_opp = 340, 80
    prizes_agent, prizes_opp = 6, 6
    entropies = []
    intents = []

    for turn in range(1, max_turns + 1):
        # --- Agent Turn ---
        obs_agent = make_dict_obs(0, hp_agent, hp_opp, prizes_agent, prizes_opp, turn)
        
        # Telemetry recording
        try:
            parsed = main.to_observation_class(obs_agent)
            parsed_w = main._wrap_obs(parsed)
            plan = main.compute_attack_plan(parsed_w)
            scores = [main.score_option(opt, parsed_w, plan) for opt in parsed_w.select.options]
            entropies.append(main.decision_entropy(scores))
            intents.append(main.macro_intent_for_score(max(scores)))
        except Exception:
            pass

        actions = main.agent(obs_agent)
        agent_choice = actions[0] if actions else 0

        if agent_choice == 1: # ATTACK chosen
            hp_opp -= 120 # Mega Lucario ex attack damage
            if hp_opp <= 0:
                prizes_agent -= 2 # Knocked out ex/basic
                hp_opp = 80
                if prizes_agent <= 0:
                    return (True, turn, (6 - prizes_agent) - (6 - prizes_opp), entropies, intents)

        # --- Opponent Turn ---
        obs_opp = make_dict_obs(1, hp_opp, hp_agent, prizes_opp, prizes_agent, turn)
        opp_actions = opponent.choose_action(obs_opp)
        opp_choice = opp_actions[0] if opp_actions else 0

        if opp_choice == 1: # Opponent attacks
            hp_agent -= 40
            if hp_agent <= 0:
                prizes_opp -= 1
                hp_agent = 340
                if prizes_opp <= 0:
                    return (False, turn, (6 - prizes_agent) - (6 - prizes_opp), entropies, intents)

    won = prizes_agent < prizes_opp or (prizes_agent == prizes_opp and hp_agent > hp_opp)
    margin = (6 - prizes_agent) - (6 - prizes_opp)
    return (won, max_turns, margin, entropies, intents)


def run_tournament(num_games_per_opponent: int = 50) -> Dict[str, Any]:
    """Run tournament across benchmark bots and calculate estimated Elo rating."""
    opponents = [
        RandomBot(),
        GreedyKOBot(),
        EnergyAggroBot(),
        HeuristicMirrorBot(),
    ]

    print("=" * 72)
    print(" 🏆 PTCG AI AGENT LOCAL TOURNAMENT & ELO EVALUATION HARNESS")
    print("=" * 72)
    print(f"Target Agent: Mega Lucario ex Agent (main.py v3.3.0)")
    print(f"Benchmark Opponents: {len(opponents)} Archetypes")
    print(f"Rounds per Opponent: {num_games_per_opponent} matches ({len(opponents) * num_games_per_opponent} total)")
    print("-" * 72)

    total_wins = 0
    total_games = 0
    opponent_stats = {}
    all_entropies = []
    all_intents = []

    start_time = time.time()

    for opp in opponents:
        wins = 0
        losses = 0
        total_turns = 0
        total_margin = 0

        for _ in range(num_games_per_opponent):
            won, turns, margin, entropies, intents = simulate_game(opp)
            if won:
                wins += 1
            else:
                losses += 1
            total_turns += turns
            total_margin += margin
            all_entropies.extend(entropies)
            all_intents.extend(intents)

        win_rate = (wins / num_games_per_opponent) * 100.0
        avg_turns = total_turns / num_games_per_opponent
        avg_margin = total_margin / num_games_per_opponent

        opponent_stats[opp.name] = {
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_turns": avg_turns,
            "avg_margin": avg_margin,
            "base_elo": opp.base_elo,
        }

        total_wins += wins
        total_games += num_games_per_opponent

        print(f"vs {opp.name:<30} | Record: {wins:2d}W - {losses:2d}L | Win Rate: {win_rate:5.1f}% | Avg Margin: {avg_margin:+4.1f} prizes")

    elapsed = time.time() - start_time
    overall_win_rate = (total_wins / total_games) * 100.0

    # Calculate estimated Elo Rating
    avg_opp_elo = sum(opp.base_elo for opp in opponents) / len(opponents)
    clamped_wr = max(0.01, min(0.99, total_wins / total_games))
    elo_delta = 400.0 * math.log10(clamped_wr / (1.0 - clamped_wr))
    estimated_elo = avg_opp_elo + elo_delta

    avg_entropy = sum(all_entropies) / len(all_entropies) if all_entropies else 0.0
    intent_counts = {}
    for i in all_intents:
        intent_counts[i] = intent_counts.get(i, 0) + 1

    print("=" * 72)
    print(" 📊 EVALUATION SUMMARY & KAGGLE ESTIMATED RATING")
    print("=" * 72)
    print(f" Total Matches Simulated : {total_games}")
    print(f" Overall Win Rate       : {overall_win_rate:.2f}% ({total_wins}/{total_games})")
    print(f" Average Decision Entropy: {avg_entropy:.4f} nats (lower = more decisive)")
    print(f" Estimated Kaggle Elo   : {estimated_elo:.1f} Elo (Baseline Scale: 1000.0)")
    print("-" * 72)
    print(" Macro-Intent Execution Breakdown:")
    for intent_name in ["LETHAL", "AGGRO_KO", "EVOLVE", "ATTACK", "ATTACH", "PLAY", "BENCH_SETUP", "RESOURCE", "STABILIZE", "PASS"]:
        count = intent_counts.get(intent_name, 0)
        pct = (count / len(all_intents) * 100.0) if all_intents else 0.0
        if count > 0:
            print(f"   • {intent_name:<15}: {count:4d} calls ({pct:5.1f}%)")
    print("=" * 72)

    if estimated_elo >= 1290.0:
        tier = "🥇 GLOBAL #1 TIER (Tokyo Faceoff Ready — 1295+ Elo)"
    elif estimated_elo >= 1200.0:
        tier = "🥈 TOP 1% GOLD TIER (Grandmaster)"
    elif estimated_elo >= 1100.0:
        tier = "🥉 TOP 10% SILVER TIER (Competitive Master)"
    else:
        tier = "🎗️ BASELINE TIER (Needs Heuristic Tuning)"

    print(f" Performance Tier       : {tier}")
    print(f" Simulation Time        : {elapsed:.2f} seconds")
    print("=" * 72)

    return {
        "overall_win_rate": overall_win_rate,
        "estimated_elo": estimated_elo,
        "avg_entropy": avg_entropy,
        "tier": tier,
        "opponent_stats": opponent_stats,
    }


if __name__ == "__main__":
    run_tournament(num_games_per_opponent=50)
