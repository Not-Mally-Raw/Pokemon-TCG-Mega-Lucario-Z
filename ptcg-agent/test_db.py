import sys, os
sys.path.insert(0, "/Users/spandankewte/Downloads/Pokemon TCG/ptcg-agent")
from agent.card_database import CardDatabase

CardDatabase.initialize()
print(f"Loaded {len(CardDatabase._card_data_cache)} cards.")
c = CardDatabase.get_card(678)
print(f"Card 678: {c.name} - Stage: {c.category}")
