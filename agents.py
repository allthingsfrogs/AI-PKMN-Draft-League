import json
import anthropic
from dotenv import load_dotenv
from models import Pokemon, Coach

load_dotenv()


class DraftAgent:
    """Wraps a Claude API call to make draft picks on behalf of a coach."""

    def __init__(self, coach: Coach, personality: str):
        self.coach = coach
        self.personality = personality
        self.client = anthropic.Anthropic()

    # ── Prompt helpers ────────────────────────────────────────────────────────

    @staticmethod
    def load_knowledge(path: str) -> str:
        with open(path) as f:
            return f.read()

    def _format_pool(self, pool: list[Pokemon]) -> str:
        """Group available Pokémon by cost tier for the prompt."""
        by_cost: dict[int, list[str]] = {}
        for p in pool:
            by_cost.setdefault(p.cost, []).append(p.name)
        lines = []
        for cost in sorted(by_cost, reverse=True):
            names = ", ".join(sorted(by_cost[cost]))
            lines.append(f"  {cost}pts: {names}")
        return "\n".join(lines)

    def _format_roster(self, roster: list[Pokemon]) -> str:
        if not roster:
            return "  (empty)"
        total = sum(p.cost for p in roster)
        return "\n".join(f"  - {p.name} ({p.cost}pts)" for p in roster) + f"\n  Total spent: {total}pts"

    def _build_system_prompt(self) -> list:
        speed_tiers = self.load_knowledge("knowledge/speed_tiers.md")
        meta_threats = self.load_knowledge("knowledge/meta_threats.md")
        league_rules = self.load_knowledge("knowledge/league_rules.md")

        return [
            {
                "type": "text",
                "text": f"""You are a Pokémon VGC draft league coach. Your drafting philosophy:
{self.personality}

{league_rules}

{speed_tiers}

{meta_threats}

It is currently your turn to make a pick for your roster.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{{"pick": "Exact Pokémon Name", "reasoning": "brief explanation"}}

In your reasoning, mention a few of the following: which Pokémon in your current roster
synergize with this pick, any threats on opponent teams you want to cover, and any
weaknesses or holes in your roster you are filling with this pick.""",
                "cache_control": {"type": "ephemeral"}
            }
        ]

    def _build_user_prompt(self, affordable: list[Pokemon], opponent_rosters: list[list[Pokemon]]) -> str:
        picks_made = len(self.coach.roster)
        picks_left = self.coach.max_roster - picks_made

        roster_str = self._format_roster(self.coach.roster)
        pool_str = self._format_pool(affordable)

        opp_lines = []
        for i, roster in enumerate(opponent_rosters):
            names = ", ".join(p.name for p in roster) if roster else "(no picks yet)"
            opp_lines.append(f"  Coach {i + 1}: {names}")
        opp_str = "\n".join(opp_lines) if opp_lines else "  (none)"

        return f"""Your roster ({picks_made}/{self.coach.max_roster} picks used, {self.coach.remaining_budget}pts remaining, {picks_left} picks left):
{roster_str}

Affordable Pokémon still available (grouped by cost):
{pool_str}

Opponents' rosters so far:
{opp_str}

Pick one Pokémon from the affordable list above."""

    # ── Core API call ─────────────────────────────────────────────────────────

    def pick(self, available_pool: list[Pokemon], opponent_rosters: list[list[Pokemon]]) -> tuple:
        """Ask Claude to choose a Pokémon. Falls back to highest-cost affordable on failure."""
        affordable = [p for p in available_pool if self.coach.can_afford(p)]

        if not affordable:
            raise ValueError(f"{self.coach.name} has no affordable Pokémon left in the pool.")

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=self._build_system_prompt(),
            messages=[{"role": "user", "content": self._build_user_prompt(affordable, opponent_rosters)}],
        )

        print(f"  cache_write: {response.usage.cache_creation_input_tokens}, cache_read: {response.usage.cache_read_input_tokens}")

        return self._parse_pick(response, affordable)

    # ── Response parsing & validation ─────────────────────────────────────────

    def _parse_pick(self, response, affordable: list[Pokemon]) -> tuple:
        text = next((b.text for b in response.content if b.type == "text"), "")

        # strip markdown code fences if Claude wraps the JSON
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        pick_name = ""
        reasoning = ""
        try:
            data = json.loads(text.strip())
            pick_name = str(data.get("pick", "")).strip()
            reasoning = str(data.get("reasoning", "")).strip()
        except (json.JSONDecodeError, AttributeError):
            pass

        # case-insensitive match against the affordable pool
        pool_map = {p.name.lower(): p for p in affordable}
        matched = pool_map.get(pick_name.lower())

        if matched:
            print(f"[{self.coach.name}] Picks {matched.name} ({matched.cost}pts) — {reasoning}")
            return matched, reasoning

        # fallback: pick the highest-cost affordable Pokémon
        fallback = max(affordable, key=lambda p: p.cost)
        print(
            f"[{self.coach.name}] Invalid pick '{pick_name}' — "
            f"falling back to {fallback.name} ({fallback.cost}pts)"
        )
        return fallback, ""
