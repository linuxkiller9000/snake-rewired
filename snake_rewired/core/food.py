"""Food system: types, spawning, expiry. Pure Python, no pygame."""

import random

FOOD_TYPES = ("normal", "bonus", "golden", "speed", "slow")

FOOD_INFO = {
    "normal": {"score": 10, "growth": 1, "effect": None},
    "bonus":  {"score": 25, "growth": 1, "effect": None},
    "golden": {"score": 50, "growth": 2, "effect": None},
    "speed":  {"score": 5,  "growth": 0, "effect": "speed"},
    "slow":   {"score": 5,  "growth": 0, "effect": "slow"},
}

# Temporary effect durations in global ticks (base tick ~0.10s -> 50 ticks ~5s).
SPEED_EFFECT_TICKS = 50
SLOW_EFFECT_TICKS = 50

# Special foods blink, then disappear if not eaten (ticks).
SPECIAL_TTL = 120
SPECIAL_BLINK_AT = 30


class FoodItem:
    __slots__ = ("kind", "pos", "age", "ttl")

    def __init__(self, kind, pos, ttl=None):
        self.kind = kind
        self.pos = pos
        self.age = 0
        self.ttl = ttl

    @property
    def expiring_soon(self):
        return self.ttl is not None and (self.ttl - self.age) <= SPECIAL_BLINK_AT

    def step(self):
        self.age += 1
        return self.ttl is not None and self.age >= self.ttl


class FoodManager:
    """Maintains the food population for a match.

    normal_target: how many normal pellets to keep on the field.
    special_chance: probability per spawn wave that a special appears.
    enabled_specials: which special kinds may appear (mode dependent).
    """

    def __init__(self, normal_target=1, special_chance=0.0, enabled_specials=(),
                 seed=None):
        self.normal_target = normal_target
        self.special_chance = special_chance
        self.enabled_specials = tuple(enabled_specials)
        self.items = {}  # pos -> FoodItem
        self.rng = random.Random(seed)
        self.max_specials = 2

    def occupied(self):
        return set(self.items)

    def at(self, pos):
        return self.items.get(pos)

    def remove(self, pos):
        return self.items.pop(pos, None)

    def _free_cells(self, arena, snakes):
        occupied = set()
        for s in snakes:
            if s.alive:
                occupied.update(s.cells)
        occupied.update(self.items)
        # Keep a one-cell margin around every head: no unfair instant spawns.
        for s in snakes:
            if s.alive:
                hx, hy = s.head
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        occupied.add((hx + dx, hy + dy))
        return list(arena.free_cells(occupied))

    def spawn_one(self, kind, arena, snakes):
        free = self._free_cells(arena, snakes)
        if not free:
            return None
        pos = self.rng.choice(free)
        ttl = SPECIAL_TTL if kind != "normal" else None
        item = FoodItem(kind, pos, ttl)
        self.items[pos] = item
        return item

    def maintain(self, arena, snakes):
        """Spawn to target counts and expire old specials. Call once per tick."""
        expired = [p for p, it in self.items.items() if it.step()]
        for p in expired:
            del self.items[p]
        normals = sum(1 for it in self.items.values() if it.kind == "normal")
        while normals < self.normal_target:
            if self.spawn_one("normal", arena, snakes) is None:
                break
            normals += 1
        specials = sum(1 for it in self.items.values() if it.kind != "normal")
        if (self.enabled_specials and specials < self.max_specials
                and self.rng.random() < self.special_chance):
            kind = self.rng.choice(self.enabled_specials)
            self.spawn_one(kind, arena, snakes)
