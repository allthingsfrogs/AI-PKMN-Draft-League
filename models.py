from dataclasses import dataclass, field

@dataclass
class Pokemon:
    name: str
    cost: int

@dataclass
class Coach:
    name: str
    budget: int = 100
    roster: list[Pokemon] = field(default_factory=list)
    max_roster: int = 10
    fa_remaining: int = 6
    trades_remaining: int = 6

    @property
    def remaining_budget(self):
        return self.budget - sum(p.cost for p in self.roster)

    def can_afford(self, pokemon: Pokemon) -> bool:
        picks_left = self.max_roster - len(self.roster)
        if picks_left <= 0:
            return False
        # reserve 1 point per remaining pick after this one
        min_reserve = picks_left - 1
        return pokemon.cost <= self.remaining_budget - min_reserve
    
    def draft(self, pokemon: Pokemon):
        self.roster.append(pokemon)
