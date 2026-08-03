"""
Kaggle Ground-Truth API Diagnostic & Verification Script (v3.3.0)
Run this script inside a Kaggle notebook cell to inspect exact runtime attribute names
for Observation, Select, Option, CardData, PlayerState, and Attack types in cg.api.
"""

import sys
import os
import dataclasses
from typing import Any

# Ensure cg package is importable
cg_dir = "/kaggle/input/competitions/pokemon-tcg-ai-battle/sample_submission/sample_submission"
if os.path.exists(cg_dir) and cg_dir not in sys.path:
    sys.path.insert(0, cg_dir)
if "." not in sys.path:
    sys.path.insert(0, ".")

import cg.api as cg
from cg.api import to_observation_class, all_card_data

print("=" * 72)
print(" 🔍 KAGGLE GROUND-TRUTH API DIAGNOSTIC HARNESS")
print("=" * 72)

# 1. CardData Inspection
db = all_card_data()
if isinstance(db, dict):
    sample_card = list(db.values())[0] if db else None
elif isinstance(db, (list, tuple)):
    sample_card = db[0] if db else None
else:
    sample_card = None

print("\n--- 1. CardData Field Inspection ---")
if sample_card:
    print(f"Type: {type(sample_card).__name__}")
    if dataclasses.is_dataclass(sample_card):
        for f in dataclasses.fields(sample_card):
            val = getattr(sample_card, f.name, None)
            print(f"  • {f.name:<20}: {type(val).__name__:<12} = {repr(val)[:60]}")
    else:
        for attr in sorted(dir(sample_card)):
            if not attr.startswith("_"):
                val = getattr(sample_card, attr, None)
                if not callable(val):
                    print(f"  • {attr:<20}: {type(val).__name__:<12} = {repr(val)[:60]}")

# 2. Check for all_attack() or Attack objects
print("\n--- 2. Attack Functionality Inspection ---")
has_all_attack = hasattr(cg, "all_attack") or "all_attack" in dir(cg)
print(f"cg.all_attack function exists: {has_all_attack}")

if sample_card and hasattr(sample_card, "attacks"):
    atks = getattr(sample_card, "attacks", [])
    print(f"Sample card attacks ({len(atks)}): {atks}")
    if atks:
        first_atk = atks[0]
        print(f"  First attack type: {type(first_atk).__name__}")
        if dataclasses.is_dataclass(first_atk):
            for f in dataclasses.fields(first_atk):
                print(f"    • {f.name}: {getattr(first_atk, f.name)}")
        elif isinstance(first_atk, dict):
            for k, v in first_atk.items():
                print(f"    • {k}: {v}")

# 3. Observation Parsing & Field Inspection
print("\n--- 3. Observation / Select / Option Parsing Inspection ---")
mock_wire = {
    "current": {
        "yourIndex": 0, "turn": 1, "turnActionCount": 0, "firstPlayer": 0,
        "supporterPlayed": False, "stadiumPlayed": False, "energyAttached": False,
        "retreated": False, "result": 0, "stadium": None, "looking": None,
        "players": [
            {"handCount": 3, "active": [{"id": 678, "serial": 1, "hp": 340, "maxHp": 340, "energies": [6]}], "bench": [], "benchMax": 5, "deckCount": 53, "discard": [], "prize": [1, 2], "hand": [1182, 6]},
            {"handCount": 3, "active": [{"id": 677, "serial": 2, "hp": 80, "maxHp": 80, "energies": [6]}], "bench": [], "benchMax": 5, "deckCount": 53, "discard": [], "prize": [1, 2], "hand": []}
        ]
    },
    "select": {
        "type": "0",
        "context": "0",
        "option": [
            {"type": "7", "area": "2", "index": 0, "card_id": 1182},
            {"type": "13", "area": "4", "index": 1, "attack_id": 0}
        ],
        "minCount": 1,
        "maxCount": 1
    },
    "logs": []
}

obs = to_observation_class(mock_wire)
print(f"to_observation_class return type: {type(obs).__name__}")

sel = getattr(obs, "select", None)
if sel:
    print(f"Select object type: {type(sel).__name__}")
    print("Select attributes:")
    has_options_attr = hasattr(sel, "options")
    has_option_attr = hasattr(sel, "option")
    has_max_count = hasattr(sel, "max_count")
    has_maxCount = hasattr(sel, "maxCount")
    print(f"  • select.options exists  : {has_options_attr}")
    print(f"  • select.option exists   : {has_option_attr}")
    print(f"  • select.max_count exists: {has_max_count}")
    print(f"  • select.maxCount exists : {has_maxCount}")

    opts = getattr(sel, "options", getattr(sel, "option", []))
    if opts:
        first_opt = opts[0]
        print(f"\nOption object type: {type(first_opt).__name__}")
        print("Option attributes:")
        for attr in ("type", "option_type", "optionType", "in_play_area", "inPlayArea", "card_id", "cardId", "attack_id", "attackId", "index"):
            val = getattr(first_opt, attr, "MISSING")
            print(f"  • opt.{attr:<15} = {repr(val)}")

print("=" * 72)
print(" ✅ GROUND-TRUTH DIAGNOSTIC COMPLETED SUCCESSFULLY")
print("=" * 72)
