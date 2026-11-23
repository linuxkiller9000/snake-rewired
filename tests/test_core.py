"""Core simulation tests: movement, growth, collisions, food, modes."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snake_rewired.core.geometry import UP, DOWN, LEFT, RIGHT
from snake_rewired.core.arena import Arena, SIZES, SPAWN_LENGTH
from snake_rewired.core.food import FoodManager, FoodItem, FOOD_TYPES
from snake_rewired.core.match import Match, PlayerSlot
from snake_rewired.core.rules import resolve_step
from snake_rewired.core.snake import Snake


class FixedCtl:
    """Controller returning a fixed or scripted direction."""
    def __init__(self, script=None):
        self.script = list(script or [])
    def next_direction(self, snake, match):
        return self.script.pop(0) if self.script else None


def make_snake(cells, direction=RIGHT, sid=1):
    return Snake(sid, f"S{sid}", list(cells), direction)


class TestMovement(unittest.TestCase):
    def test_moves_one_cell_per_tick(self):
        arena = Arena("nokia", "medium", "none")
        s = make_snake([(5, 5), (4, 5), (3, 5)])
        resolve_step([s], [s], arena, FoodManager(), 1, [])
        self.assertEqual(s.head, (6, 5))
        self.assertEqual(s.length, 3)

    def test_no_reverse(self):
        s = make_snake([(5, 5), (4, 5), (3, 5)])
        self.assertFalse(s.set_direction(LEFT))   # reversal rejected
        self.assertTrue(s.set_direction(UP))
        self.assertFalse(s.set_direction(DOWN))   # pending UP, DOWN reverses it

    def test_queued_turn_applies(self):
        arena = Arena("nokia", "medium", "none")
        s = make_snake([(5, 5), (4, 5), (3, 5)])
        s.set_direction(UP)
        resolve_step([s], [s], arena, FoodManager(), 1, [])
        self.assertEqual(s.head, (5, 4))

    def test_two_turns_in_one_tick_cannot_reverse(self):
        # Pressing LEFT then UP before the tick must not reverse the snake.
        s = make_snake([(5, 5), (4, 5), (3, 5)])
        s.set_direction(LEFT)  # rejected (reversal)
        s.set_direction(UP)    # accepted
        s.consume_turn()
        self.assertEqual(s.direction, UP)


class TestCollisions(unittest.TestCase):
    def setUp(self):
        self.arena = Arena("nokia", "medium", "none")

    def test_wall_death(self):
        s = make_snake([(0, 5), (1, 5), (2, 5)])
        s.direction = LEFT
        events = []
        resolve_step([s], [s], self.arena, FoodManager(), 1, events)
        self.assertFalse(s.alive)
        self.assertEqual(s.elimination_reason, "wall")

    def test_self_collision(self):
        # Square loop: head at (5,5) moving RIGHT into own body.
        s = make_snake([(5, 5), (5, 6), (6, 6), (6, 5), (5, 4)], RIGHT)
        events = []
        resolve_step([s], [s], self.arena, FoodManager(), 1, events)
        self.assertFalse(s.alive)
        self.assertEqual(s.elimination_reason, "self")

    def test_body_collision_other_snake(self):
        # b advances; its old head cell is filled by its own following body,
        # so a entering that cell dies (classic rule).
        a = make_snake([(7, 4), (7, 5), (7, 6)], RIGHT, sid=1)
        b = make_snake([(8, 4), (8, 5), (8, 6)], RIGHT, sid=2)
        events = []
        resolve_step([a, b], [a, b], self.arena, FoodManager(), 1, events)
        self.assertFalse(a.alive)
        self.assertEqual(a.elimination_reason, "body")
        self.assertTrue(b.alive)

    def test_body_death(self):
        # a drives into b's stationary body.
        a = make_snake([(7, 5), (7, 6), (7, 7)], RIGHT, sid=1)
        b = make_snake([(8, 5), (8, 6), (8, 7)], UP, sid=2)
        events = []
        resolve_step([a], [a, b], self.arena, FoodManager(), 1, events)
        self.assertFalse(a.alive)
        self.assertEqual(a.elimination_reason, "body")

    def test_tail_vacates_is_safe(self):
        # a chases b's tail; b moves on, a survives entering the old tail cell.
        a = make_snake([(5, 9), (5, 10), (5, 11)], RIGHT, sid=1)
        b = make_snake([(7, 9), (6, 9), (5, 9)], RIGHT, sid=2)  # b tail at a's head?
        # rebuild cleanly: b ahead of a, both moving RIGHT, a follows b's tail
        b.cells.clear(); b.cells.extend([(7, 5), (6, 5), (5, 5)])
        b.direction = RIGHT
        a.cells.clear(); a.cells.extend([(4, 5), (3, 5), (2, 5)])
        a.direction = RIGHT  # target (5,5): b's tail, which vacates
        events = []
        resolve_step([a, b], [a, b], self.arena, FoodManager(), 1, events)
        self.assertTrue(a.alive, "tail cell vacates, entry must be safe")
        self.assertEqual(a.head, (5, 5))

    def test_headon_both_die(self):
        a = make_snake([(5, 5), (5, 6), (5, 7)], RIGHT, sid=1)
        b = make_snake([(7, 5), (7, 6), (7, 7)], LEFT, sid=2)
        events = []
        resolve_step([a, b], [a, b], self.arena, FoodManager(), 1, events)
        self.assertFalse(a.alive)
        self.assertFalse(b.alive)
        self.assertEqual(a.elimination_reason, "headon")
        self.assertEqual(b.elimination_reason, "headon")

    def test_head_swap_both_die(self):
        a = make_snake([(5, 5), (5, 6), (5, 7)], RIGHT, sid=1)
        b = make_snake([(6, 5), (6, 6), (6, 7)], LEFT, sid=2)
        events = []
        resolve_step([a, b], [a, b], self.arena, FoodManager(), 1, events)
        self.assertFalse(a.alive)
        self.assertFalse(b.alive)
        self.assertEqual(a.elimination_reason, "swap")

    def test_simultaneous_fairness_no_order_advantage(self):
        # Same setup, reversed list order: same outcome.
        def run(order):
            a = make_snake([(5, 5), (5, 6), (5, 7)], RIGHT, sid=1)
            b = make_snake([(7, 5), (7, 6), (7, 7)], LEFT, sid=2)
            pair = [a, b] if order == 0 else [b, a]
            resolve_step(pair, pair, Arena("nokia", "medium", "none"),
                         FoodManager(), 1, [])
            return a.alive, b.alive
        self.assertEqual(run(0), run(1))

    def test_obstacle_death(self):
        arena = Arena("industrial", "medium", "pillars")
        cell = next(iter(arena.obstacles))
        s = make_snake([(cell[0] - 1, cell[1]), (cell[0] - 2, cell[1]),
                        (cell[0] - 3, cell[1])], RIGHT)
        events = []
        resolve_step([s], [s], arena, FoodManager(), 1, events)
        self.assertFalse(s.alive)
        self.assertEqual(s.elimination_reason, "obstacle")


class TestFood(unittest.TestCase):
    def setUp(self):
        self.arena = Arena("nokia", "medium", "none")

    def test_eat_grows_and_scores(self):
        fm = FoodManager(seed=1)
        fm.items[(6, 5)] = FoodItem("normal", (6, 5))
        s = make_snake([(5, 5), (4, 5), (3, 5)])
        resolve_step([s], [s], self.arena, fm, 1, [])
        self.assertEqual(s.score, 10)
        self.assertEqual(s.food_eaten, 1)
        # growth pending: tail kept this step; length grows by 1 overall
        self.assertEqual(s.length, 4)

    def test_golden_grows_two(self):
        fm = FoodManager(seed=1)
        fm.items[(6, 5)] = FoodItem("golden", (6, 5))
        s = make_snake([(5, 5), (4, 5), (3, 5)])
        resolve_step([s], [s], self.arena, fm, 1, [])
        self.assertEqual(s.score, 50)
        resolve_step([s], [s], self.arena, fm, 2, [])
        self.assertEqual(s.length, 5)

    def test_speed_effect_steps_twice_and_expires(self):
        fm = FoodManager(seed=1)
        fm.items[(6, 5)] = FoodItem("speed", (6, 5))
        s = make_snake([(5, 5), (4, 5), (3, 5)])
        resolve_step([s], [s], self.arena, fm, 1, [])
        self.assertEqual(s.speed_effect, "speed")
        self.assertEqual(s.steps_for_tick(2), 2)
        s.effect_ticks = 1
        s.tick_effects()
        self.assertIsNone(s.speed_effect)
        self.assertEqual(s.steps_for_tick(3), 1)

    def test_slow_effect_skips_alternate_ticks(self):
        s = make_snake([(5, 5), (4, 5), (3, 5)])
        s.apply_effect("slow", 10)
        self.assertEqual(s.steps_for_tick(2), 1)
        self.assertEqual(s.steps_for_tick(3), 0)

    def test_food_never_spawns_occupied(self):
        fm = FoodManager(normal_target=20, seed=3)
        snakes = [make_snake([(5, 5), (4, 5), (3, 5)])]
        for _ in range(30):
            fm.maintain(self.arena, snakes)
        occupied = set(snakes[0].cells)
        for pos in fm.items:
            self.assertNotIn(pos, occupied)
            self.assertFalse(self.arena.is_blocked(pos))

    def test_specials_expire(self):
        fm = FoodManager(seed=1)
        item = FoodItem("bonus", (6, 5), ttl=3)
        fm.items[(6, 5)] = item
        s = make_snake([(20, 20), (19, 20), (18, 20)])
        for _ in range(3):
            fm.maintain(self.arena, s and [s])
        self.assertNotIn((6, 5), fm.items)


class TestArena(unittest.TestCase):
    def test_sizes(self):
        for size, (c, r) in SIZES.items():
            a = Arena("neon", size)
            self.assertEqual((a.cols, a.rows), (c, r))

    def test_six_spawns_distinct_and_clear(self):
        for theme in ("nokia", "neon", "industrial", "circuit", "minimal"):
            for size in SIZES:
                a = Arena(theme, size)
                spawns = a.spawn_points(6)
                heads = [s[0] for s in spawns]
                self.assertEqual(len(set(heads)), 6)
                for head, d, cells in spawns:
                    for c in cells:
                        self.assertTrue(a.in_bounds(c))
                        self.assertNotIn(c, a.obstacles)
                # no two spawn bodies overlap
                allcells = [c for _, _, cells in spawns for c in cells]
                self.assertEqual(len(allcells), len(set(allcells)))

    def test_spawn_direction_never_into_wall_immediately(self):
        a = Arena("circuit", "small")
        for head, d, cells in a.spawn_points(6):
            nxt = (head[0] + d[0], head[1] + d[1])
            self.assertTrue(a.in_bounds(nxt))

    def test_obstacle_patterns_symmetric(self):
        for pattern in ("pillars", "walls", "cross", "dots"):
            a = Arena("industrial", "medium", pattern)
            for (x, y) in a.obstacles:
                self.assertFalse((x < 2 or y < 2), "obstacles keep edge margin")


class TestMatch(unittest.TestCase):
    def test_classic_solo_runs_and_ends(self):
        p = PlayerSlot(0, "P1")
        m = Match("classic", [p], arena_theme="nokia", seed=1)
        m.attach_controller(0, FixedCtl())
        # Drive into a wall eventually with no input.
        for _ in range(20000):
            m.update(0.05)
            if m.over:
                break
        self.assertTrue(m.over)
        self.assertEqual(m.result["mode"], "classic")
        self.assertEqual(len(m.result["rankings"]), 1)

    def test_battle_last_alive_wins(self):
        players = [PlayerSlot(i, f"P{i+1}") for i in range(4)]
        m = Match("battle", players, arena_theme="neon", seed=2)
        for p in players:
            m.attach_controller(p.sid, FixedCtl())
        for _ in range(30000):
            m.update(0.05)
            if m.over:
                break
        self.assertTrue(m.over)
        self.assertEqual(len(m.result["rankings"]), 4)
        self.assertIsNotNone(m.result["winner_sid"])

    def test_battle_survivor_ranks_first(self):
        # P1 loops in a small square; everyone else drives straight and dies.
        players = [PlayerSlot(i, f"P{i+1}") for i in range(3)]
        m = Match("battle", players, arena_theme="neon", seed=2)
        loop = [UP, LEFT, DOWN, RIGHT] * 400
        m.attach_controller(0, FixedCtl(loop))
        m.attach_controller(1, FixedCtl())
        m.attach_controller(2, FixedCtl())
        for _ in range(30000):
            m.update(0.05)
            if m.over:
                break
        self.assertTrue(m.over)
        self.assertTrue(m.result["rankings"][0]["alive"])
        self.assertEqual(m.result["rankings"][0]["sid"], 0)

    def test_score_race_time_limit(self):
        players = [PlayerSlot(i, f"P{i+1}") for i in range(2)]
        m = Match("score_race", players, arena_theme="minimal",
                  duration=5, seed=3)
        for p in players:
            m.attach_controller(p.sid, FixedCtl())
        t = 0.0
        while not m.over and t < 10:
            m.update(0.05)
            t += 0.05
        self.assertTrue(m.over)
        self.assertLessEqual(m.time, 5.0 + m.base_interval + 0.01)

    def test_team_survival_team_win(self):
        players = [PlayerSlot(0, "A1", team=0), PlayerSlot(1, "A2", team=0),
                   PlayerSlot(2, "B1", team=1), PlayerSlot(3, "B2", team=1)]
        m = Match("team_survival", players, arena_theme="neon", duration=600,
                  seed=4)
        for p in players:
            m.attach_controller(p.sid, FixedCtl())
        for _ in range(40000):
            m.update(0.05)
            if m.over:
                break
        self.assertTrue(m.over)
        self.assertIsNotNone(m.result["winning_team"])
        self.assertIn(m.result["winning_team"], (0, 1))

    def test_six_player_match_completes(self):
        players = [PlayerSlot(i, f"P{i+1}") for i in range(6)]
        m = Match("battle", players, arena_theme="circuit", arena_size="large",
                  seed=5)
        for p in players:
            m.attach_controller(p.sid, FixedCtl())
        for _ in range(60000):
            m.update(0.05)
            if m.over:
                break
        self.assertTrue(m.over)
        self.assertEqual(len(m.result["rankings"]), 6)

    def test_invalid_player_count_rejected(self):
        with self.assertRaises(ValueError):
            Match("battle", [PlayerSlot(0, "A")])

    def test_classic_accepts_bots_and_ends_when_all_dead(self):
        # Classic is the merged solo entry: alone or with bots.
        players = [PlayerSlot(0, "P1"), PlayerSlot(1, "Bot", kind="bot")]
        m = Match("classic", players, arena_theme="nokia", seed=3)
        for p in players:
            m.attach_controller(p.sid, FixedCtl())
        for _ in range(60000):
            m.update(0.05)
            if m.over:
                break
        self.assertTrue(m.over)
        self.assertEqual(len(m.result["rankings"]), 2)

    def test_classic_still_rejects_over_six_players(self):
        players = [PlayerSlot(i, f"P{i}") for i in range(7)]
        with self.assertRaises(ValueError):
            Match("classic", players)


if __name__ == "__main__":
    unittest.main(verbosity=2)
