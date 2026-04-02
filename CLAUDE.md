# CLAUDE.md

## Project Overview

AI-powered Pokémon VGC draft league simulator. Multiple Claude-powered agents
autonomously draft teams, negotiate trades, and battle on a local Pokémon Showdown
server. See PROJECT_SPEC.md for the full architecture and milestone plan.

## Tech Stack

- Python 3.11+
- `anthropic` SDK for Claude API calls
- `poke-env` for Showdown integration (Milestone 5+)
- Local Pokémon Showdown server via Node.js (Milestone 5+)

## Key Files

- `PROJECT_SPEC.md` — Full architecture, rules, milestones, and design decisions
- `models.py` — Core dataclasses: Pokemon, Coach
- `agents.py` — DraftAgent (and later BattleAgent) wrapping Claude API calls
- `draft_engine.py` — Snake draft logic, pick validation
- `personalities.py` — Prompt strings that define each agent's playstyle
- `data/draft_board.csv` — The draft pool with Pokémon names and point costs (1–20)

## Conventions

- All agent decisions go through the Claude API and return structured JSON
- Always validate agent picks against the available pool — Claude can hallucinate names
- Every agent response should have a fallback path for malformed or invalid output
- Keep prompts lean: don't include info Claude already knows (type chart, basic VGC)
- Use python-dotenv to load ANTHROPIC_API_KEY from .env (never hardcode keys)

## League Rules (quick reference)

- 8 coaches, snake draft, 10 picks each, 100-point budget
- VGC Doubles format, Level 50, best-of-3
- Bring 6 of 10 to each battle
- Scoring: 2-0 = 3pts, 2-1 = 2pts, 1-2 = 1pt, 0-2 = 0pts
- 6 trades and 6 FA pickups per team through Week 3
- Top 4 make playoffs (1v4, 2v3)

## Current Milestone

Milestone 1 — Parse draft board CSV, create data model, make one successful
Claude API call that returns a valid draft pick.

## How to Help

- When writing agent prompts, keep them specific to the current game state
- When I share draft results, help me analyze team compositions and suggest prompt tweaks
- Prefer simple, readable code over clever abstractions — this is a learning project
- If I ask you to write something, check PROJECT_SPEC.md first for context
- Never read, write, display, or reference .env files or their contents
