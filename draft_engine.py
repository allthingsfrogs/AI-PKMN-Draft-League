import os
import sys
import csv
import json
from dotenv import load_dotenv
from models import Pokemon, Coach
from agents import DraftAgent
from personalities import AGGRESSIVE, DEFENSIVE, ALL_AROUNDER, WEATHER, WILDCARD, MEMER, BULKY_OFFENSE
from datetime import datetime

load_dotenv()

DRAFT_BOARD = os.getenv("DRAFT_BOARD_PATH")

def load_draft_board() -> list[Pokemon]:
    pool = []
    with open(DRAFT_BOARD) as f:
        for row in csv.DictReader(f):
            pool.append(Pokemon(name=row["name"], cost=int(row["cost"])))
    return pool


def get_snake_order(num_coaches: int, rounds: int) -> list[int]:
    # return flat list of coach indices in snake order
    order = []
    for r in range(rounds):
        indices = range(num_coaches)
        order.extend(reversed(indices) if r % 2 else indices)
    return order

def run_draft():
    
    pool = load_draft_board()

    coaches = [
        Coach("Ada Lovelace"),
        Coach("John Von Neumann"),
        Coach("Yann LeCun"),
        Coach("Geoffrey Hinton"),
        Coach("Grace Hopper"),
        Coach("John McCarthy"),
        Coach("Alan Turing"),
        Coach("Linus Tech Tips")
    ]

    agents = [
        DraftAgent(coaches[0], ALL_AROUNDER),
        DraftAgent(coaches[1], DEFENSIVE),
        DraftAgent(coaches[2], AGGRESSIVE),
        DraftAgent(coaches[3], WEATHER),
        DraftAgent(coaches[4], WILDCARD),
        DraftAgent(coaches[5], WEATHER),
        DraftAgent(coaches[6], BULKY_OFFENSE),
        DraftAgent(coaches[7], MEMER)
    ]

    # get current date and time
    now = datetime.now()

    # format as a custom string (e.g., "2024-03-31 14:30:05")
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")

    draft_log = {
        "draft_time": dt_string,
        "picks": []
    }

    snake_order = get_snake_order(len(coaches), rounds=10)

    for pick_num, coach_idx in enumerate(snake_order, start=1):

        agent = agents[coach_idx]
        coach = coaches[coach_idx]

        # all other coaches' rosters
        opponent_rosters = [c.roster for i, c in enumerate(coaches) if i != coach_idx]

        # agent asks Claude, returns a validated Pokemon object
        chosen, reasoning = agent.pick(pool, opponent_rosters)

        # remove from pool so no one else can take it
        pool = [p for p in pool if p.name != chosen.name]

        # add to the coach's roster
        coach.draft(chosen)

        # create a log_entry, append to draft_log.json
        log_entry = {
            "pick_number": pick_num,
            "round": (pick_num - 1) // len(coaches) + 1,
            "coach": coach.name,
            "playstyle": agent.personality,
            "pokemon": chosen.name,
            "cost": chosen.cost,
            "budget_remaining": coach.remaining_budget,
            "reasoning": reasoning
        }
        draft_log["picks"].append(log_entry)

        print(f"Pick {pick_num}: {coach.name} drafts {chosen.name}")
    
    with open("outputs/draft_log.json", "w") as f:
        json.dump(draft_log, f, indent=2)