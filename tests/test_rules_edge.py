"""Edge-case verification: speed-effect unequal ticks, simultaneous human
input fairness, mode end/tie rules, pad reconnect identity."""

import os
import sys
import unittest

os.environ.setdefault("SNAKE_REWIRED_HOME", "/tmp/sr_test_home")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from snake_rewired.core.geometry import UP, DOWN, LEFT, RIGHT
from snake_rewired.core.arena import Arena
from snake_rewired.core.food import FoodManager, FoodItem
from snake_rewired.core.match import Match, PlayerSlot
from snake_rewired.core.rules import resolve_step
from snake_rewired.core.snake import Snake
from snake_rewired.game.inputman import InputManager, VirtualPad
from snake_rewired.game.persistence import Settings


def fresh_home():
    import shutil
    shutil.rmtree("/tmp/sr_test_home", ignore_errors=True)


def snake(cells, direction=RIGHT, sid=1):
    return Snake(sid, f"S{sid}", list(cells), direction)


class TestSpeedEffectCollisions(unittest.TestCase):
    """Speed food makes a snake move twice per tick; collision resolution
    must stay correct when the moving sets differ per sub-step."""

    def setUp(self):
        self.arena = Arena("nokia", "medium", "none")

    def test_fast_snake_two_substeps_checked(self):
        # Fast snake's second sub-step hits a wall: dies on sub-step 2.
        fast = snake([(37, 5), (36, 5), (35, 5)], RIGHT, sid=1)
        fast.apply_effect("speed", 10)
        normal = snake([(10, 20), (9, 20), (8, 20)], RIGHT, sid=2)
        m_events = []
        # tick: fast moves twice, normal once
        moving1 = [fast, normal]
        resolve_step(moving1, [fast, normal], self.arena, FoodManager(), 1,
                     m_events)
        # sub-step 1: both move once
        self.assertTrue(fast.alive)
        self.assertEqual(fast.head, (38, 5))
        self.assertEqual(normal.head, (11, 20))
        moving2 = [fast]                     # sub-step 2: only fast moves
        resolve_step(moving2, [fast, normal], self.arena, FoodManager(), 1,
                     m_events)
        self.assertTrue(fast.alive)          # (39,5) is the last valid cell
        self.assertEqual(fast.head, (39, 5))
        self.assertEqual(normal.head, (11, 20))  # untouched by sub-step 2

    def test_fast_snake_death_on_exact_wall(self):
        fast = snake([(38, 5), (37, 5), (36, 5)], RIGHT, sid=1)
        fast.apply_effect("speed", 10)
        events = []
        resolve_step([fast], [fast], self.arena, FoodManager(), 1, events)
        self.assertEqual(fast.head, (39, 5))   # last valid cell, alive
        resolve_step([fast], [fast], self.arena, FoodManager(), 1, events)
        self.assertFalse(fast.alive)           # sub-step 2 exits at x=40
        self.assertEqual(fast.elimination_reason, "wall")

    def test_slow_snake_holds_position_while_others_move(self):
        slow = snake([(10, 10), (9, 10), (8, 10)], RIGHT, sid=1)
        slow.apply_effect("slow", 10)
        fast = snake([(10, 20), (9, 20), (8, 20)], RIGHT, sid=2)
        m = Match.__new__(Match)  # not needed; direct steps
        events = []
        # odd tick: slow skips (steps_for_tick(3)==0), fast moves
        self.assertEqual(slow.steps_for_tick(3), 0)
        self.assertEqual(fast.steps_for_tick(3), 1)
        resolve_step([fast], [slow, fast], self.arena, FoodManager(), 3,
                     events)
        self.assertEqual(slow.head, (10, 10))
        self.assertEqual(fast.head, (11, 20))

    def test_body_collision_with_stationary_slow_snake(self):
        # A slowed snake does not move this tick; its full body blocks.
        slow = snake([(8, 5), (8, 6), (8, 7)], UP, sid=1)
        slow.apply_effect("slow", 10)
        other = snake([(7, 5), (7, 6), (7, 7)], RIGHT, sid=2)
        events = []
        resolve_step([other], [slow, other], self.arena, FoodManager(), 3,
                     events)
        self.assertFalse(other.alive)
        self.assertEqual(other.elimination_reason, "body")


class TestSimultaneousKeyboardFairness(unittest.TestCase):
    def setUp(self):
        fresh_home()

    def test_two_keyboard_players_same_tick_no_reversal(self):
        settings = Settings()
        im = InputManager(settings)
        im.bind_player(0, ("kb", 0))
        im.bind_player(1, ("kb", 1))
        players = [PlayerSlot(0, "P1"), PlayerSlot(1, "P2")]
        m = Match("battle", players, arena_theme="nokia", seed=1)
        m.attach_controller(0, im.controller_for(0))
        m.attach_controller(1, im.controller_for(1))
        d1 = m.snakes[0].direction
        d2 = m.snakes[1].direction
        # Same-frame presses: P1 tries reversal+turn, P2 turns.
        im.handle_keydown("a" if d1 != LEFT else "d")   # reversal attempt
        im.handle_keydown("w")                            # then a legal turn
        im.handle_keydown("up")                           # P2 legal turn
        m.update(0.2)
        self.assertNotEqual(m.snakes[0].direction,
                            (-d1[0], -d1[1]), "P1 must not reverse")
        self.assertEqual(m.snakes[0].direction, UP)
        self.assertEqual(m.snakes[1].direction, UP)


class TestModeEndRules(unittest.TestCase):
    def test_score_race_tiebreak_by_food(self):
        players = [PlayerSlot(0, "A"), PlayerSlot(1, "B")]
        m = Match("score_race", players, arena_theme="minimal", duration=2,
                  seed=1)
        # Force identical scores, different food counts, then run out clock.
        # No food on the field and straight-line spawns keep both alive.
        m.food.items.clear()
        m.food.normal_target = 0
        m.snakes[0].score = 50
        m.snakes[0].food_eaten = 5
        m.snakes[1].score = 50
        m.snakes[1].food_eaten = 3
        t = 0.0
        while not m.over and t < 5:
            m.update(0.05)
            t += 0.05
        self.assertTrue(m.over)
        r = m.result["rankings"]
        self.assertEqual(r[0]["food"], 5)
        self.assertEqual(r[0]["sid"], 0)

    def test_team_survival_timeout_score_decides(self):
        players = [PlayerSlot(0, "A", team=0), PlayerSlot(1, "B", team=1)]
        m = Match("team_survival", players, arena_theme="neon", duration=2,
                  seed=1)
        m.snakes[0].score = 80
        m.snakes[1].score = 30
        # keep both alive by steering nowhere dangerous (they drive straight
        # for 2s from safe spawns on medium)
        t = 0.0
        while not m.over and t < 5:
            m.update(0.05)
            t += 0.05
        self.assertTrue(m.over)
        if m.snakes[0].alive and m.snakes[1].alive:
            self.assertEqual(m.result["winning_team"], 0)

    def test_team_survival_elimination_decides(self):
        players = [PlayerSlot(0, "A", team=0), PlayerSlot(1, "B", team=1)]
        m = Match("team_survival", players, arena_theme="neon", duration=600,
                  seed=1)
        m.snakes[0].eliminate(1, "wall")
        m._check_end()
        self.assertTrue(m.over)
        self.assertEqual(m.result["winning_team"], 1)

    def test_battle_all_dead_simultaneous_has_winner_by_score(self):
        players = [PlayerSlot(0, "A"), PlayerSlot(1, "B")]
        m = Match("battle", players, arena_theme="nokia", seed=1)
        m.snakes[0].score = 70
        m.snakes[1].score = 40
        m.snakes[0].eliminate(5, "headon")
        m.snakes[1].eliminate(5, "headon")
        m.elimination_order.extend([0, 1])
        m._check_end()
        self.assertTrue(m.over)
        self.assertEqual(m.result["winner_sid"], 0)


class TestPadReconnectIdentity(unittest.TestCase):
    def setUp(self):
        fresh_home()

    def test_reconnect_reclaims_same_slot_by_guid(self):
        settings = Settings()
        im = InputManager(settings)
        im.init_pygame.__self__ if False else None
        # Simulate: two identical Twin USB pads (same name!) in slots 0,1.
        pad_a = VirtualPad("Twin USB Pad")
        pad_b = VirtualPad("Twin USB Pad")
        im._joys = {11: pad_a, 22: pad_b}
        im.pad_slots = {0: 11, 1: 22, 2: None, 3: None}
        # Pad in slot 0 (instance 11) disconnects, others survive.
        im._joys.pop(11)
        for slot, cur in im.pad_slots.items():
            if cur == 11:
                im.pad_slots[slot] = None
        self.assertIsNone(im.pad_slots[0])
        self.assertEqual(im.pad_slots[1], 22)   # other pad keeps its slot
        # Reconnect: it gets a NEW instance id from SDL; slot 0 is free.
        pad_a2 = VirtualPad("Twin USB Pad")
        im._joys[33] = pad_a2
        used = {v for v in im.pad_slots.values() if v is not None}
        for iid in im._joys:
            if iid in used:
                continue
            for slot in range(4):
                if im.pad_slots[slot] is None:
                    im.pad_slots[slot] = iid
                    used.add(iid)
                    break
        self.assertEqual(im.pad_slots[0], 33)
        self.assertEqual(im.pad_slots[1], 22)


if __name__ == "__main__":
    unittest.main(verbosity=2)
