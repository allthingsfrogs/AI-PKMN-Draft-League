# Wolfey Draft League — AI Agent Project Spec

> Reference document for building an AI-powered Pokémon VGC draft league simulator.
> Generated from a Claude.ai design session. Open this in Claude Code with
> "read PROJECT_SPEC.md" to get up to speed.

---

## 1. Project Goal

Build a Python system where multiple AI agents (powered by Claude via the Anthropic API)
autonomously participate in a Pokémon VGC draft league: drafting teams, making trades,
building battle rosters, and playing Doubles matches on a local Pokémon Showdown server.

---

## 2. League Rules (from Wolfey Draft League)

### Draft
- 8 coaches, snake draft format (1→8, 8→1, repeat)
- Draft order is randomized
- Each coach drafts 10 Pokémon with a 100-point budget
- Pokémon cost 1–20 points (tiers defined in draft board CSV)

### Free Agency & Trades
- 6 free agency pickups per team, allowed through end of Week 3
- 6 inter-team trades per team, allowed through end of Week 3
- 24-hour grace period after Week 3: unlimited FA and trades

### Battles
- VGC Doubles format, Level 50
- Best-of-3 each week
- Bring 6 Pokémon to each battle (from roster of 10)
- Closed teamsheets, but Tera Types shared at team preview
- Standard VGC rules and clauses

### Scoring
- 2-0 win = 3 pts
- 2-1 win = 2 pts
- 1-2 loss = 1 pt
- 0-2 loss = 0 pts

### Tiebreakers (in order)
1. Wins
2. Points
3. Differential
4. Head-to-head
5. Strength of schedule

### Playoffs
- Top 4 coaches qualify
- Seed 1 vs Seed 4, Seed 2 vs Seed 3
- 6-week regular season

---

## 3. Architecture Overview

Five layers, each with a clear responsibility:

```
┌─────────────────────────────────────────────────────────┐
│  DESIGN LAYER — Claude.ai                               │
│  You + Claude design the system, iterate on prompts,    │
│  generate docs and reports. Not part of the runtime.    │
└────────────────────────┬────────────────────────────────┘
                         │ you copy generated code
                         ▼
┌─────────────────────────────────────────────────────────┐
│  PYTHON PROJECT — Your Machine                          │
│  Central hub. Orchestrates everything.                  │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ │
│  │  Draft    │ │  Season  │ │  Showdown │ │  Agents   │ │
│  │  Engine   │ │  Manager │ │  Client   │ │  (Claude) │ │
│  └────┬─────┘ └────┬─────┘ └─────┬─────┘ └─────┬─────┘ │
└───────┼────────────┼─────────────┼──────────────┼───────┘
        │            │             │              │
        │            │             ▼              ▼
        │            │   ┌─────────────────┐ ┌──────────┐
        │            │   │ SHOWDOWN SERVER │ │ CLAUDE   │
        │            │   │ localhost:8000  │ │ API      │
        │            │   │ Runs battles,   │ │ Makes    │
        │            │   │ you spectate    │ │ every    │
        │            │   │ in browser      │ │ decision │
        │            │   └─────────────────┘ └──────────┘
        │            │
        ▼            ▼
  ┌──────────────────────┐
  │ DATA / OUTPUTS       │
  │ draft_log.json       │
  │ rosters.json         │
  │ standings.json       │
  │ scouting_reports/    │
  └──────────────────────┘
```

### What talks to what
- **Your code → Claude API**: Prompts containing game state → JSON decisions back
- **Your code → Showdown**: Battle commands via WebSocket → State updates back
- **Your browser → Showdown**: Spectate live at localhost:8000
- **Claude API → Showdown**: NEVER. Claude never touches Showdown directly. Python is always the middleman.

---

## 4. Data Model

### Pokemon
```python
@dataclass
class Pokemon:
    name: str
    cost: int          # 1–20 points (from draft board CSV)
```

### Coach
```python
@dataclass
class Coach:
    name: str
    budget: int = 100
    roster: list[Pokemon] = field(default_factory=list)
    max_roster: int = 10
    fa_remaining: int = 6
    trades_remaining: int = 6
```

Key methods:
- `remaining_budget` — budget minus sum of roster costs
- `can_afford(pokemon)` — checks cost against budget, reserving 1 pt per remaining pick
- `draft(pokemon)` — adds to roster, no validation (engine handles that)

### DraftEngine
Manages the draft pool and snake order:
- `get_draft_order()` — generates 80-pick snake sequence (10 rounds × 8 coaches)
- `remove_pokemon(name)` — pops from available pool
- `get_available_for_coach(coach)` — filters by affordability

### SeasonManager (later milestone)
Tracks weekly schedule, standings, tiebreakers, and playoff bracket.

---

## 5. Agent Design

### How agents work
An agent wraps a Claude API call with league-aware context. It does NOT call any
external service — it receives a text description of the current state and returns
a JSON decision. Your Python code handles all external interaction.

### DraftAgent
```
Input:  available pool (grouped by cost), current roster, budget, opponent rosters
Output: {"pick": "Pokemon Name", "reasoning": "..."}
```

### BattleAgent (later milestone)
```
Input:  Doubles field state — 2 active mons per side, HP, weather, terrain, boosts,
        available moves with targets, switch options
Output: {"slot1": {"action": "move", "target": "Rage Fist", "tera": false},
         "slot2": {"action": "switch", "target": "Incineroar", "tera": false},
         "reasoning": "..."}
```

### TradeAgent (later milestone)
```
Input:  own roster, opponent roster, league context
Output: {"propose": true, "offer": "...", "want": "...", "reasoning": "..."}
         or {"accept": true/false, "reasoning": "..."}
```

### Personality system
Each agent gets a personality string that shapes its strategy. Examples:
- Aggressive: prioritizes speed, sweepers, setup, burst damage
- Defensive: prioritizes bulk, Intimidate, redirection, recovery
- Weather: builds around sun/rain/sand/hail setters and abusers
- Wildcard: takes creative risks, niche picks, surprise strategies

Personalities are just prompt strings stored in personalities.py. Tuning them is
the main way you improve agent behavior over time.

### Knowledge layers (for battle agents)
1. **Built-in** — Claude already knows type matchups, common sets, VGC fundamentals
2. **System prompt docs** — Your reference files: speed tiers, meta threats, league pool
3. **Scouting data** — Per-opponent history built from match results (what they brought, Tera usage, lead patterns)

---

## 6. Showdown Integration (later milestone)

### Local server setup
```bash
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown
npm install
node pokemon-showdown start --no-security
```

### Agent connection
Use the `poke-env` Python library. Each agent is a subclass of `poke_env.Player`
with its own Showdown account. You override `choose_move(battle)` to call Claude.

### Doubles battle turn cycle
1. Showdown sends field state (2 mons per side, HP, weather, terrain, boosts)
2. Python parses into readable text description
3. Claude picks 2 actions (one per active slot) + targeting + Tera decision
4. Python translates JSON → Showdown command (e.g. `/choose move 1 2, switch 3`)
5. Both players' commands sent → Showdown resolves the turn
6. Repeat until one side is out of Pokémon

### Spectating
Open localhost:8000 in your browser. You'll see the battle room with full
animations, HP bars, move announcements. Replays are saved automatically.

---

## 7. File Structure

```
wolfey-draft-ai/
├── main.py                 # Entry point
├── models.py               # Pokemon, Coach dataclasses
├── draft_engine.py         # Snake draft, pick validation
├── agents.py               # DraftAgent (+ BattleAgent later)
├── personalities.py        # Personality prompt strings
├── board_parser.py         # CSV → list[Pokemon]
├── trades.py               # Trade + free agency logic (milestone 3)
├── season.py               # Schedule, standings, playoffs (milestone 4)
├── showdown_client.py      # ClaudePlayer + state formatter (milestone 5)
├── knowledge/              # Reference docs loaded into agent prompts
│   ├── vgc_rules.md
│   ├── speed_tiers.md
│   └── meta_threats.md
├── data/
│   └── draft_board.csv     # Wolfey Draft League CSV
├── outputs/
│   ├── draft_log.json
│   ├── rosters.json
│   └── standings.json
├── .env                    # ANTHROPIC_API_KEY=sk-ant-...
└── requirements.txt        # anthropic, poke-env (when needed)
```

---

## 8. Milestones (build in this order)

### Milestone 1 — One agent, one pick
**Goal**: Prove the core concept works.
- [ ] Parse draft board CSV into list[Pokemon] with names and costs
- [ ] Create Coach dataclass with budget tracking
- [ ] Make one Claude API call with the available pool
- [ ] Parse the JSON response and validate the pick exists
- [ ] Print the result

**You write**: board_parser.py, models.py
**Claude helps with**: agents.py, prompt structure, debugging

### Milestone 2 — Full draft simulation
**Goal**: 8 agents complete a 10-round snake draft.
- [ ] Build DraftEngine with snake order and pick validation
- [ ] Create 4–8 agents with distinct personalities
- [ ] Run the full 80-pick draft in a loop
- [ ] Add fallback logic for invalid picks (hallucinated names)
- [ ] Log every pick with reasoning to draft_log.json
- [ ] Print final rosters with budget spent

**Key risk**: Claude may hallucinate Pokémon names not in the pool. Always
validate picks against the available list and have a fallback (pick the
highest-cost affordable Pokémon).

### Milestone 3 — Trades and free agency
**Goal**: Agents negotiate roster changes.
- [ ] Implement propose_trade() — Agent A proposes, Agent B evaluates
- [ ] Implement free_agency_pick() — Agent evaluates drops and pickups
- [ ] Track trade/FA counts per coach (6 each, through Week 3)
- [ ] Log all transactions

### Milestone 4 — Season management
**Goal**: Automate the weekly schedule and standings.
- [ ] Build round-robin schedule (6 weeks, 4 matchups per week)
- [ ] Implement scoring (3/2/1/0 points)
- [ ] Implement tiebreaker logic
- [ ] Generate playoff bracket (top 4)
- [ ] Track and display standings after each week

### Milestone 5 — Showdown battles
**Goal**: Agents play actual VGC Doubles matches.
- [ ] Install and run local Showdown server
- [ ] Install poke-env, create bot accounts
- [ ] Write state_formatter.py — converts poke-env Battle → text prompt
- [ ] Write ClaudePlayer — subclass of poke-env Player, calls Claude API
- [ ] Handle Doubles-specific logic: 2 actions per turn, targeting, Tera
- [ ] Run a test match and spectate in browser
- [ ] Wire into season manager for automated weekly matchups

### Milestone 6 — Scouting and adaptation
**Goal**: Agents learn from match history.
- [ ] Record what each coach brings, leads with, Teras
- [ ] Build per-opponent scouting reports
- [ ] Feed scouting data into pre-match team selection prompts
- [ ] Agents adjust team picks based on opponent tendencies

---

## 9. Cost Estimates

Using Claude Sonnet (recommended for this project):
- Input: $3 / million tokens
- Output: $15 / million tokens

| Activity                    | Tokens per instance | Instances per season | Estimated cost |
|-----------------------------|--------------------:|---------------------:|---------------:|
| Draft pick                  | ~4,000              | 80                   | ~$1            |
| Trade negotiation           | ~3,000              | ~50                  | ~$0.50         |
| Battle turn (Doubles)       | ~4,000              | ~3,000               | ~$40           |
| Team selection              | ~3,000              | ~60                  | ~$0.60         |
| **Full season total**       |                     |                      | **~$40–80**    |

With prompt caching (90% discount on repeated system prompts): **~$15–30**

---

## 10. Key Dependencies

| Package             | What it does                          | When you need it   |
|---------------------|---------------------------------------|--------------------|
| `anthropic`         | Claude API client                     | Milestone 1        |
| `python-dotenv`     | Load API key from .env                | Milestone 1        |
| `poke-env`          | Showdown WebSocket client + state     | Milestone 5        |
| `pokemon-showdown`  | Local battle server (Node.js)         | Milestone 5        |

---

## 11. Tips

**Prompt engineering is your main lever.** The difference between an agent that
drafts well and one that wastes budget on bad picks comes down to how you write
the prompt. Iterate on personality strings and system prompts frequently.

**Always validate Claude's output.** LLMs can hallucinate names, return malformed
JSON, or pick Pokémon that were already drafted. Every agent response needs
validation with a fallback path.

**Start without Showdown.** Milestones 1–4 are a complete, satisfying project on
their own. You'll have a working draft simulator with trades, standings, and
playoffs. Showdown battles are a major expansion — treat them as a separate phase.

**Use prompt caching.** Your system prompt (rules, meta knowledge, personality)
stays the same across many calls. Anthropic's prompt caching feature gives you a
90% discount on those repeated tokens.

**Keep battle state prompts lean.** During battles, every turn is an API call.
Don't dump the full type chart every turn — Claude already knows it. Only include
what changes: field state, HP, weather, available moves.

**Test one agent against a hardcoded strategy first.** Before running agent-vs-agent
battles, test your BattleAgent against a simple scripted opponent (always uses
move 1, for example). This isolates bugs in your Showdown client from bugs in
your agent logic.
