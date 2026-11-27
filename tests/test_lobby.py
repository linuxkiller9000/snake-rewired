"""Tests for the device-led lobby, full-bleed layout, and calm music."""

import os
import sys
import unittest

os.environ.setdefault("SNAKE_REWIRED_HOME", "/tmp/sr_lobby_test_home")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from snake_rewired.core.arena import Arena
from snake_rewired.game.app import App
from snake_rewired.game.inputman import VirtualPad
from snake_rewired.game.render import Layout, LOGICAL_W
from snake_rewired.game.screens.setup import SetupScreen
from snake_rewired.game import audio as audio_mod


def fresh_home():
    import shutil
    shutil.rmtree("/tmp/sr_lobby_test_home", ignore_errors=True)


def key_event(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


class TestLobby(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        fresh_home()
        self.app = App(headless=True)

    def tearDown(self):
        self.app.running = False

    def setup_screen(self, mode_key):
        s = SetupScreen(self.app, mode_key)
        self.app.push_screen(s)
        return s

    def test_classic_default_solo_and_bot_join_leave(self):
        s = self.setup_screen("classic")
        self.assertEqual([e["device"] for e in s.roster], [("kb", 0)])
        s.handle_event(key_event(pygame.K_b))
        s.handle_event(key_event(pygame.K_b))
        bots = [e for e in s.roster if e["device"][0] == "bot"]
        self.assertEqual(len(bots), 2)
        self.assertEqual(bots[0]["difficulty"], "normal")
        s.handle_event(key_event(pygame.K_x))
        bots = [e for e in s.roster if e["device"][0] == "bot"]
        self.assertEqual(len(bots), 1)

    def test_wasd_join_leave_with_w_and_s(self):
        s = self.setup_screen("battle")
        # Joined by default: S navigates (never removes), Delete on the
        # focused row removes, W re-joins, no duplicates.
        s.handle_event(key_event(pygame.K_s))
        self.assertTrue(any(e["device"] == ("kb", 0) for e in s.roster))
        s.focus = ("roster", 0)
        s.handle_event(key_event(pygame.K_DELETE))
        self.assertFalse(any(e["device"] == ("kb", 0) for e in s.roster))
        s.handle_event(key_event(pygame.K_w))
        s.handle_event(key_event(pygame.K_w))
        joined = [e for e in s.roster if e["device"] == ("kb", 0)]
        self.assertEqual(len(joined), 1)

    def test_arrows_join_leave_with_up_down(self):
        s = self.setup_screen("battle")
        s.handle_event(key_event(pygame.K_DOWN))   # navigates, kb2 stays
        self.assertTrue(any(e["device"] == ("kb", 1) for e in s.roster))
        idx = [i for i, e in enumerate(s.roster) if e["device"] == ("kb", 1)][0]
        s.focus = ("roster", idx)
        s.handle_event(key_event(pygame.K_BACKSPACE))   # kb2 leaves
        self.assertFalse(any(e["device"] == ("kb", 1) for e in s.roster))
        s.handle_event(key_event(pygame.K_UP))     # kb2 joins
        self.assertTrue(any(e["device"] == ("kb", 1) for e in s.roster))

    def test_pad_join_leave_with_buttons(self):
        self.app.input.pad_slots[0] = 4242
        self.app.input._joys[4242] = VirtualPad("Twin USB Pad")
        s = self.setup_screen("battle")
        join = pygame.event.Event(pygame.JOYBUTTONDOWN, button=0,
                                  instance_id=4242)
        s.handle_event(join)
        self.assertTrue(any(e["device"] == ("pad", 0) for e in s.roster))
        leave = pygame.event.Event(pygame.JOYBUTTONDOWN, button=1,
                                   instance_id=4242)
        s.handle_event(leave)
        self.assertFalse(any(e["device"] == ("pad", 0) for e in s.roster))

    def test_lobby_caps_at_six_players(self):
        s = self.setup_screen("battle")
        for _ in range(8):
            s._add_bot()
        self.assertEqual(len(s.roster), 6)

    def test_bot_difficulty_cycle_on_focused_row(self):
        s = self.setup_screen("battle")
        s._add_bot()
        bot_index = next(i for i, e in enumerate(s.roster)
                         if e["device"][0] == "bot")
        s.focus = ("roster", bot_index)
        s._adjust(1)
        self.assertEqual(s.roster[bot_index]["difficulty"], "hard")
        s._adjust(-1)
        s._adjust(-1)
        self.assertEqual(s.roster[bot_index]["difficulty"], "easy")

    def test_tab_navigation_wraps(self):
        s = self.setup_screen("battle")
        first = s.focus_rows[0]
        s.focus = first
        s._move_focus(-1)
        self.assertEqual(s.focus, s.focus_rows[-1])
        s._move_focus(1)
        self.assertEqual(s.focus, first)

    def test_roster_start_builds_players(self):
        s = self.setup_screen("battle")
        s._add_bot()
        s._start()
        from snake_rewired.game.screens.play import PlayScreen
        self.assertIsInstance(self.app.current, PlayScreen)
        kinds = [p.kind for p in self.app.current.match.players.values()]
        self.assertEqual(kinds, ["human", "human", "bot"])


class TestLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_arena_uses_full_window_width(self):
        layout = Layout(Arena("neon", "medium", "none"))
        # No sidebar: the arena is wider than the old sidebar layout
        # allowed (logical width minus 300px sidebar and margins).
        self.assertGreater(layout.rect.width, LOGICAL_W - 300 - 36)
        self.assertFalse(hasattr(layout, "sidebar"))


class TestMusic(unittest.TestCase):
    def test_calm_loop_is_long_varied_and_normalized(self):
        samples = audio_mod._music_loop()
        seconds = len(samples) / audio_mod.SAMPLE_RATE
        self.assertGreaterEqual(seconds, 20.0)   # not a short loop
        peak = max(abs(v) for v in samples)
        self.assertLessEqual(peak, 0.96)
        # Many distinct note frequencies across the loop (varied melody).
        self.assertGreater(len(audio_mod._CHORDS), 2)
        self.assertGreater(len(audio_mod._PHRASES), 1)
        self.assertNotEqual(audio_mod._PHRASES[0], audio_mod._PHRASES[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
