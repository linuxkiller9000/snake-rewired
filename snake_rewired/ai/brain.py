"""AI snake brains. Pure Python, no pygame.

Three difficulties, all bound by the same movement and collision rules as
humans - one queued turn per tick, same speed, full information limits of
the shared grid (the AI reads the same public match state a human sees).

EASY:   greedy toward the nearest food with one-step death avoidance and
        occasional random mistakes.
NORMAL: BFS pathfinding to food, rejects moves that trap it in too little
        reachable space, falls back to surviving (chase open space).
HARD:   NORMAL plus opponent awareness (avoids cells enemy heads can reach
        next step, prefers food it can reach before opponents), and a
        stronger space evaluation.
"""

import random
from collections import deque

from ..core.geometry import DIRECTIONS, add, opposite, manhattan


class AIBrain:
    def __init__(self, difficulty="normal", seed=None, mistake_rate=None):
        assert difficulty in ("easy", "normal", "hard")
        self.difficulty = difficulty
        self.rng = random.Random(seed)
        self.mistake_rate = mistake_rate
        self._last_dir = None
        self._cache_tick = None
        self._cache_blocked = None
        self._cache_tails = None

    def _sets(self, match):
        """Per-tick memo of blocked cells and vacating tails: every helper
        in a tick shares one computation."""
        if self._cache_tick != match.tick:
            blocked = set(match.arena.obstacles)
            tails = set()
            for s in match.snakes.values():
                if s.alive:
                    blocked.update(s.cells)
                    if s.growth == 0:
                        tails.add(s.tail)
            self._cache_tick = match.tick
            self._cache_blocked = blocked
            self._cache_tails = tails
        return self._cache_blocked, self._cache_tails

    # ------------------------------------------------------------------
    def next_direction(self, snake, match):
        if self.difficulty == "easy":
            return self._easy(snake, match)
        if self.difficulty == "normal":
            return self._normal(snake, match)
        return self._hard(snake, match)

    # -- shared helpers ---------------------------------------------------
    @staticmethod
    def _blocked_cells(match, moving_tail_ok=True):
        """Cells occupied at this instant (all snakes' bodies)."""
        blocked = set(match.arena.obstacles)
        for s in match.snakes.values():
            if s.alive:
                blocked.update(s.cells)
        return blocked

    @staticmethod
    def _tails_that_vacate(match):
        out = set()
        for s in match.snakes.values():
            if s.alive and s.growth == 0:
                out.add(s.tail)
        return out

    def _safe_moves(self, snake, match, avoid_danger_zone=False):
        """Candidate directions that do not die immediately."""
        occ, tails = self._sets(match)
        blocked = occ - tails
        danger = set()
        if avoid_danger_zone:
            for s in match.snakes.values():
                if s.alive and s.sid != snake.sid and s.length >= snake.length:
                    for d in DIRECTIONS:
                        danger.add(add(s.head, d))
        out = []
        for d in DIRECTIONS:
            if opposite(snake.direction, d):
                continue
            cell = add(snake.head, d)
            if not match.arena.in_bounds(cell) or cell in blocked:
                continue
            if avoid_danger_zone and cell in danger:
                continue
            out.append(d)
        return out

    def _reachable_space(self, start, match, cap=400):
        """Flood fill size from a cell (post-move safety estimate)."""
        occ, tails = self._sets(match)
        blocked = occ - tails
        if start in blocked or not match.arena.in_bounds(start):
            return 0
        seen = {start}
        q = deque([start])
        while q and len(seen) < cap:
            cur = q.popleft()
            for d in DIRECTIONS:
                nxt = add(cur, d)
                if (nxt not in seen and nxt not in blocked
                        and match.arena.in_bounds(nxt)):
                    seen.add(nxt)
                    q.append(nxt)
        return len(seen)

    def _bfs_path(self, start, goal, match, extra_blocked=()):
        occ, tails = self._sets(match)
        blocked = (occ | set(extra_blocked)) - tails
        blocked.discard(start)
        if goal in blocked and goal not in match.food.items:
            return None
        blocked.discard(goal)
        q = deque([start])
        prev = {start: None}
        while q:
            cur = q.popleft()
            if cur == goal:
                path = []
                while cur != start:
                    path.append(cur)
                    cur = prev[cur]
                path.reverse()
                return path
            for d in DIRECTIONS:
                nxt = add(cur, d)
                if (nxt not in prev and nxt not in blocked
                        and match.arena.in_bounds(nxt)):
                    prev[nxt] = cur
                    q.append(nxt)
        return None

    def _nearest_food(self, snake, match):
        if not match.food.items:
            return None
        head = snake.head
        return min(match.food.items.values(),
                   key=lambda it: manhattan(head, it.pos))

    # -- difficulties -------------------------------------------------------
    def _easy(self, snake, match):
        safe = self._safe_moves(snake, match)
        if not safe:
            return None
        # Mistakes: sometimes pick a random safe move.
        rate = self.mistake_rate if self.mistake_rate is not None else 0.22
        if self.rng.random() < rate:
            return self.rng.choice(safe)
        food = self._nearest_food(snake, match)
        if food is None:
            return self.rng.choice(safe)
        safe.sort(key=lambda d: manhattan(add(snake.head, d), food.pos))
        return safe[0]

    def _normal(self, snake, match):
        safe = self._safe_moves(snake, match)
        if not safe:
            return None
        food = self._nearest_food(snake, match)
        if food is not None:
            path = self._bfs_path(snake.head, food.pos, match)
            if path:
                step = path[0]
                d = (step[0] - snake.head[0], step[1] - snake.head[1])
                if d in safe and self._reachable_space(step, match) >= max(
                        snake.length, 12):
                    return d
        # No good route to food: maximize breathing room.
        return max(safe, key=lambda d: self._reachable_space(
            add(snake.head, d), match))

    def _hard(self, snake, match):
        safe_all = self._safe_moves(snake, match)
        if not safe_all:
            return None
        # Danger zone: cells enemy heads can enter next step. We avoid them
        # when possible but still cross them for a good enough prize.
        danger = set()
        for s in match.snakes.values():
            if s.alive and s.sid != snake.sid and s.length >= snake.length:
                for d in DIRECTIONS:
                    danger.add(add(s.head, d))

        best = None        # (score, direction) without danger entry
        best_risky = None  # (score, direction) whose first step is in danger
        for item in match.food.items.values():
            path = self._bfs_path(snake.head, item.pos, match)
            if not path:
                continue
            dist = len(path)
            step = path[0]
            d = (step[0] - snake.head[0], step[1] - snake.head[1])
            if d not in safe_all:
                continue
            if self._reachable_space(step, match) < max(snake.length, 14):
                continue
            enemy_dist = min((manhattan(s.head, item.pos)
                              for s in match.snakes.values()
                              if s.alive and s.sid != snake.sid), default=999)
            value = {"golden": 5, "bonus": 3, "normal": 1,
                     "speed": 2, "slow": 0.5}.get(item.kind, 1)
            score = value - 0.15 * dist
            if enemy_dist < dist:
                score -= 1.0          # likely contested
            if step in danger:
                score -= 2.0          # risky entry
                if best_risky is None or score > best_risky[0]:
                    best_risky = (score, d)
                continue
            if best is None or score > best[0]:
                best = (score, d)
        if best is not None:
            return best[1]
        if best_risky is not None and best_risky[0] > -1.0:
            return best_risky[1]
        # Survival: maximize open space, prefer staying out of danger.
        safe_calm = [d for d in safe_all if add(snake.head, d) not in danger]
        pool = safe_calm or safe_all
        return max(pool, key=lambda d: self._reachable_space(
            add(snake.head, d), match))
