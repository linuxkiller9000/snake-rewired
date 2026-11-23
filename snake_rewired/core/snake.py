"""Snake simulation entity. Pure Python, no pygame."""

from collections import deque

from .geometry import opposite

# Speed-effect multipliers expressed as steps per global tick.
STEPS_NORMAL = 1
STEPS_FAST = 2          # speed food: two cells per tick
SLOW_PERIOD = 2         # slow food: move once every SLOW_PERIOD ticks


class Snake:
    """A single snake on the grid.

    cells is head-first: cells[0] is the head, cells[-1] is the tail.
    """

    __slots__ = (
        "sid", "name", "team", "cells", "direction", "pending",
        "alive", "score", "food_eaten", "growth", "born_tick",
        "eliminated_tick", "elimination_reason", "survival_ticks",
        "speed_effect", "effect_ticks", "kills",
    )

    def __init__(self, sid, name, cells, direction, team=None):
        self.sid = sid
        self.name = name
        self.team = team
        self.cells = deque(cells)  # head first
        self.direction = direction
        self.pending = None        # queued direction for next step
        self.alive = True
        self.score = 0
        self.food_eaten = 0
        self.growth = 0            # pending extra length from eating
        self.kills = 0
        self.born_tick = 0
        self.eliminated_tick = None
        self.elimination_reason = None
        self.survival_ticks = 0
        self.speed_effect = None   # None | "speed" | "slow"
        self.effect_ticks = 0

    @property
    def head(self):
        return self.cells[0]

    @property
    def tail(self):
        return self.cells[-1]

    @property
    def length(self):
        return len(self.cells)

    def set_direction(self, new_dir):
        """Queue a turn. Reversal into our own neck is rejected here and
        again at consumption time (two queued turns could otherwise
        combine into a reversal)."""
        if new_dir is None:
            return False
        base = self.pending if self.pending is not None else self.direction
        if opposite(base, new_dir) or base == new_dir:
            return False
        self.pending = new_dir
        return True

    def consume_turn(self):
        """Apply the queued turn for this step (never a reversal)."""
        if self.pending is not None and not opposite(self.direction, self.pending):
            self.direction = self.pending
        self.pending = None

    def steps_for_tick(self, tick):
        """How many movement steps this snake takes in the given tick."""
        if not self.alive:
            return 0
        if self.speed_effect == "speed":
            return STEPS_FAST
        if self.speed_effect == "slow":
            return 1 if (tick % SLOW_PERIOD) == 0 else 0
        return STEPS_NORMAL

    def tick_effects(self):
        """Advance temporary effects by one global tick."""
        if self.speed_effect is not None:
            self.effect_ticks -= 1
            if self.effect_ticks <= 0:
                self.speed_effect = None
                self.effect_ticks = 0

    def apply_effect(self, kind, ticks):
        self.speed_effect = kind
        self.effect_ticks = ticks

    def eliminate(self, tick, reason):
        self.alive = False
        self.eliminated_tick = tick
        self.elimination_reason = reason
        self.pending = None
        self.speed_effect = None
        self.effect_ticks = 0
