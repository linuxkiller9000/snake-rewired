"""AI behavior tests."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snake_rewired.ai.brain import AIBrain
from snake_rewired.core.match import Match, PlayerSlot


def run_bot_match(difficulty, seed, ticks=6000):
    """One bot alone on a classic arena; returns (alive, food_eaten, tick).

    Uses Classic Solo (single snake, ends on death) with the brain attached
    as the controller - the mode only cares about player count.
    """
    players = [PlayerSlot(0, "Bot")]
    m = Match("classic", players, arena_theme="nokia", arena_size="medium",
              seed=seed)
    brain = AIBrain(difficulty, seed=seed)
    m.attach_controller(0, brain)
    while not m.over and m.tick < ticks:
        m.update(0.05)
    s = m.snakes[0]
    return s.alive, s.food_eaten, m.tick


class TestAI(unittest.TestCase):
    def test_easy_collects_food(self):
        alive, food, tick = run_bot_match("easy", seed=11)
        self.assertGreater(food, 2, "easy bot should find some food")

    def test_normal_survives_longer_and_eats_more(self):
        # Over several seeds, NORMAL should outlast and out-eat EASY on
        # average. Not every seed: mistakes are stochastic.
        easy_food = norm_food = 0
        easy_ticks = norm_ticks = 0
        for seed in (1, 2, 3, 4, 5):
            ea, ef, et = run_bot_match("easy", seed=seed)
            na, nf, nt = run_bot_match("normal", seed=seed)
            easy_food += ef; norm_food += nf
            easy_ticks += et; norm_ticks += nt
        self.assertGreater(norm_food, easy_food)
        self.assertGreater(norm_ticks, easy_ticks)

    def test_hard_outsurvives_normal_on_average(self):
        norm_ticks = hard_ticks = 0
        norm_food = hard_food = 0
        for seed in (1, 2, 3, 4, 5):
            na, nf, nt = run_bot_match("normal", seed=seed + 40)
            ha, hf, ht = run_bot_match("hard", seed=seed + 40)
            norm_ticks += nt; hard_ticks += ht
            norm_food += nf; hard_food += hf
        self.assertGreaterEqual(hard_ticks, norm_ticks)
        self.assertGreaterEqual(hard_food, norm_food)

    def test_hard_bot_wins_battle_against_easy(self):
        # Head-to-head: hard bots should win most seeded duels vs easy bots.
        hard_wins = 0
        for seed in range(6):
            players = [PlayerSlot(0, "Easy", kind="bot", difficulty="easy"),
                       PlayerSlot(1, "Hard", kind="bot", difficulty="hard")]
            m = Match("battle", players, arena_theme="nokia",
                      arena_size="medium", seed=seed)
            m.attach_controller(0, AIBrain("easy", seed=seed))
            m.attach_controller(1, AIBrain("hard", seed=seed + 100))
            while not m.over and m.tick < 8000:
                m.update(0.05)
            if m.result and m.result["winner_sid"] == 1:
                hard_wins += 1
        self.assertGreaterEqual(hard_wins, 4, f"hard won {hard_wins}/6")

    def test_six_ai_battle_completes(self):
        players = [PlayerSlot(i, f"B{i}", kind="bot",
                              difficulty=("easy", "normal", "hard")[i % 3])
                   for i in range(6)]
        m = Match("battle", players, arena_theme="circuit",
                  arena_size="large", seed=9)
        for p in players:
            m.attach_controller(p.sid, AIBrain(p.difficulty, seed=p.sid))
        while not m.over and m.tick < 20000:
            m.update(0.05)
        self.assertTrue(m.over)
        self.assertEqual(len(m.result["rankings"]), 6)

    def test_ai_never_cheats_speed(self):
        # AI snakes obey the same one-step-per-tick movement as humans.
        players = [PlayerSlot(0, "B", kind="bot", difficulty="hard"),
                   PlayerSlot(1, "D", kind="bot", difficulty="easy")]
        m = Match("battle", players, arena_theme="nokia", seed=5)
        m.attach_controller(0, AIBrain("hard", seed=1))
        m.attach_controller(1, AIBrain("easy", seed=2))
        last_heads = {}
        for _ in range(300):
            m.update(0.1)
            for s in m.snakes.values():
                if not s.alive:
                    continue
                prev = last_heads.get(s.sid)
                if prev is not None:
                    dist = abs(s.head[0] - prev[0]) + abs(s.head[1] - prev[1])
                    self.assertLessEqual(dist, 2,  # speed food may double-step
                                         "snake moved faster than rules allow")
                last_heads[s.sid] = s.head
            if m.over:
                break


if __name__ == "__main__":
    unittest.main(verbosity=2)
