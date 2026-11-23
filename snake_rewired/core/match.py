"""Match orchestration: players, timer, eliminations, results.

Pure Python, no pygame. Rendering and input devices live in game/; a Match
only needs per-snake "controllers" - objects with next_direction(snake,
match) - which may wrap human input queues, AI brains, or test scripts.
"""

import itertools

from .arena import Arena
from .food import FoodManager
from .modes import MODES, SPEEDS, CLASSIC_RAMP_STEP, CLASSIC_RAMP_FLOOR
from .rules import resolve_step
from .snake import Snake


class PlayerSlot:
    """Static configuration for one participant."""

    def __init__(self, sid, name, kind="human", difficulty="normal",
                 team=None, color=0, pattern="solid", head="classic"):
        assert kind in ("human", "bot")
        self.sid = sid
        self.name = name
        self.kind = kind
        self.difficulty = difficulty
        self.team = team
        self.color = color
        self.pattern = pattern
        self.head = head


class Match:
    def __init__(self, mode_key, players, arena_theme="nokia",
                 arena_size="medium", speed="normal", duration=None,
                 obstacles=None, seed=None):
        if mode_key not in MODES:
            raise ValueError(f"unknown mode {mode_key!r}")
        self.mode = MODES[mode_key]
        if not self.mode.min_players <= len(players) <= self.mode.max_players:
            raise ValueError(
                f"{self.mode.title} needs {self.mode.min_players}-"
                f"{self.mode.max_players} players, got {len(players)}")
        if not self.mode.allow_bots and any(p.kind == "bot" for p in players):
            raise ValueError(f"{self.mode.title} does not allow bots")
        self.speed_key = speed
        self.base_interval = SPEEDS[speed]
        self.duration = duration if duration is not None else self.mode.default_duration
        self.arena = Arena(arena_theme, arena_size,
                           obstacles if self.mode.allow_obstacles else "none")
        self.players = {p.sid: p for p in players}
        self.controllers = {}  # sid -> controller with next_direction()
        self.snakes = {}
        spawns = self.arena.spawn_points(len(players))
        for p, (pos, d, cells) in zip(players, spawns):
            self.snakes[p.sid] = Snake(p.sid, p.name, cells, d, team=p.team)
        self.food = FoodManager(
            normal_target=self.mode.food_normal_target,
            special_chance=self.mode.food_special_chance,
            enabled_specials=self.mode.food_specials,
            seed=seed)
        self.tick = 0
        self.time = 0.0
        self.accum = 0.0
        self.prev_cells = {}  # sid -> cell list before the latest step
        self.events = []            # drained by the caller each update
        self.elimination_order = [] # sids in death order (simultaneous share)
        self.over = False
        self.result = None
        # Prime the field with normal food.
        for _ in range(self.food.normal_target):
            self.food.spawn_one("normal", self.arena, self.alive_snakes())

    # -- setup ------------------------------------------------------------
    def attach_controller(self, sid, controller):
        self.controllers[sid] = controller

    # -- state ------------------------------------------------------------
    def alive_snakes(self):
        return [s for s in self.snakes.values() if s.alive]

    def tick_interval(self):
        if self.mode.classic_ramp and self.snakes:
            s = next(iter(self.snakes.values()))
            return max(CLASSIC_RAMP_FLOOR,
                       self.base_interval - CLASSIC_RAMP_STEP * s.food_eaten)
        return self.base_interval

    def interpolation_alpha(self):
        """Fraction of the current tick elapsed, for render smoothing."""
        interval = self.tick_interval()
        if interval <= 0:
            return 1.0
        return min(1.0, self.accum / interval)

    @property
    def time_remaining(self):
        if not self.mode.timed or not self.duration:
            return None
        return max(0.0, self.duration - self.time)

    # -- simulation -------------------------------------------------------
    def update(self, dt):
        """Advance real time; run global ticks when due. Returns events."""
        if self.over:
            return []
        self.events = []
        self.accum += dt
        # Never run more than 5 ticks per update (spiral-of-death guard).
        guard = 0
        while self.accum >= self.tick_interval() and not self.over and guard < 5:
            self.accum -= self.tick_interval()
            self.time += self.tick_interval()
            self._run_tick()
            guard += 1
        if guard == 5:
            self.accum = 0.0
        return self.events

    def _run_tick(self):
        self.tick += 1
        alive = self.alive_snakes()
        for s in alive:
            s.survival_ticks += 1
            # Poll controllers once per tick (queued turn applies to all
            # steps of this tick; reversal checks make this safe).
            ctl = self.controllers.get(s.sid)
            if ctl is not None:
                d = ctl.next_direction(s, self)
                if d is not None:
                    s.set_direction(d)
        steps = max((s.steps_for_tick(self.tick) for s in alive), default=0)
        for i in range(steps):
            moving = [s for s in alive if s.alive and s.steps_for_tick(self.tick) > i]
            for s in moving:
                self.prev_cells[s.sid] = list(s.cells)
            resolve_step(moving, list(self.snakes.values()), self.arena,
                         self.food, self.tick, self.events)
        for s in alive:
            if s.alive:
                s.tick_effects()
            elif s.eliminated_tick == self.tick:
                self.elimination_order.append(s.sid)
        self.food.maintain(self.arena, self.alive_snakes())
        self._check_end()

    # -- endings ----------------------------------------------------------
    def _team_alive(self, team):
        return any(s.alive and s.team == team for s in self.snakes.values())

    def _check_end(self):
        alive = self.alive_snakes()
        m = self.mode
        if m.key == "classic":
            if not alive:
                self._finish()
            return
        if m.teams:
            teams = {s.team for s in self.snakes.values()}
            alive_teams = [t for t in teams if self._team_alive(t)]
            if len(alive_teams) <= 1:
                self._finish()
                return
        elif m.survival_win and not m.timed:
            if len(alive) <= 1:
                self._finish()
                return
        else:
            if not alive:
                self._finish()
                return
        if m.timed and self.time_remaining is not None and self.time_remaining <= 0:
            self._finish()

    def _finish(self):
        self.over = True
        self.result = self._build_result()
        self.events.append(("match_over", self.result))

    def _build_result(self):
        m = self.mode
        snakes = list(self.snakes.values())
        # Ranking: survivors outrank the eliminated; snakes eliminated on
        # a LATER tick rank higher; snakes eliminated on the SAME tick are
        # true ties, broken by score, then food, then survival time.
        def rank_key(s):
            return (
                1 if s.alive else 0,
                s.eliminated_tick if s.eliminated_tick is not None else 0,
                s.score, s.food_eaten, s.survival_ticks,
            )

        ordered = sorted(snakes, key=rank_key, reverse=True)
        rankings = []
        for place, s in enumerate(ordered, start=1):
            rankings.append({
                "sid": s.sid, "name": s.name, "place": place,
                "alive": s.alive, "score": s.score, "food": s.food_eaten,
                "length": s.length, "survival_ticks": s.survival_ticks,
                "team": s.team, "kind": self.players[s.sid].kind,
                "reason": s.elimination_reason,
            })
        winner = ordered[0] if ordered else None
        team_scores = None
        winning_team = None
        if m.teams:
            team_scores = {}
            for s in snakes:
                team_scores.setdefault(s.team, 0)
                team_scores[s.team] += s.score
            teams = sorted(team_scores,
                           key=lambda t: (self._team_alive(t), team_scores[t]),
                           reverse=True)
            winning_team = teams[0] if teams else None
        return {
            "mode": m.key,
            "winner_sid": winner.sid if winner else None,
            "winner_name": winner.name if winner else None,
            "winning_team": winning_team,
            "team_scores": team_scores,
            "rankings": rankings,
            "ticks": self.tick,
            "duration": self.time,
        }
