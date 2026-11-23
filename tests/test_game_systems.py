"""Tests for input mapping, persistence, and settings."""

import os
import sys
import unittest

os.environ.setdefault("SNAKE_REWIRED_HOME", "/tmp/sr_test_home")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from snake_rewired.core.geometry import UP, DOWN, LEFT, RIGHT
from snake_rewired.game.inputman import (InputManager, KeyboardDevice,
                                         PadMapping, VirtualPad,
                                         HumanController)
from snake_rewired.game.persistence import (Settings, SaveGame,
                                            DEFAULT_SETTINGS)


def fresh_home():
    import shutil
    shutil.rmtree("/tmp/sr_test_home", ignore_errors=True)


class TestKeyboard(unittest.TestCase):
    def setUp(self):
        fresh_home()
        self.settings = Settings()

    def test_default_mapping_two_players_share_keyboard(self):
        kb = KeyboardDevice(self.settings)
        self.assertEqual(kb.lookup("w"), (0, "up"))
        self.assertEqual(kb.lookup("d"), (0, "right"))
        self.assertEqual(kb.lookup("up"), (1, "up"))
        self.assertEqual(kb.lookup("left"), (1, "left"))
        self.assertIsNone(kb.lookup("x"))

    def test_simultaneous_presses_both_registered(self):
        im = InputManager(self.settings)
        im.bind_player(0, ("kb", 0))
        im.bind_player(1, ("kb", 1))
        self.assertTrue(im.handle_keydown("w"))
        self.assertTrue(im.handle_keydown("left"))
        self.assertEqual(im.controllers[0].next_direction(None, None), UP)
        self.assertEqual(im.controllers[1].next_direction(None, None), LEFT)

    def test_remap_replaces_conflicting_key(self):
        kb = KeyboardDevice(self.settings)
        kb.remap(0, "up", "up")  # steal P2's up arrow
        self.assertEqual(kb.lookup("up"), (0, "up"))
        # P2's "up" mapping is cleared, its other keys intact
        self.assertEqual(kb.lookup("down"), (1, "down"))

    def test_settings_persist_remap(self):
        kb = KeyboardDevice(self.settings)
        kb.remap(0, "up", "i")
        self.settings.save()
        s2 = Settings()
        self.assertEqual(s2.get("keys_p1")["up"], "i")


class TestPads(unittest.TestCase):
    def setUp(self):
        fresh_home()
        self.settings = Settings()
        self.mapping = PadMapping(self.settings)

    def test_hat_directions(self):
        pad = VirtualPad()
        for hat, d in [((0, 1), UP), ((0, -1), DOWN), ((-1, 0), LEFT),
                       ((1, 0), RIGHT)]:
            pad.set_hat(hat)
            self.assertEqual(self.mapping.direction_from_state(pad), d)

    def test_buttons_when_no_hat(self):
        pad = VirtualPad()
        self.settings.set("pad_use_hat", False)
        pad.set_button(12, 1)  # default up
        self.assertEqual(self.mapping.direction_from_state(pad), UP)
        pad.set_button(12, 0)
        pad.set_button(15, 1)  # right
        self.assertEqual(self.mapping.direction_from_state(pad), RIGHT)

    def test_stick_when_enabled(self):
        pad = VirtualPad()
        self.settings.set("pad_use_hat", False)
        self.settings.set("pad_buttons", {})
        pad.set_axis(1, -0.8)
        self.assertEqual(self.mapping.direction_from_state(pad), UP)
        pad.set_axis(1, 0.0)
        pad.set_axis(0, 0.9)
        self.assertEqual(self.mapping.direction_from_state(pad), RIGHT)

    def test_stick_never_mandatory(self):
        pad = VirtualPad()
        self.settings.set("pad_use_stick", False)
        self.settings.set("pad_buttons", {})
        pad.set_axis(0, 1.0)
        self.assertIsNone(self.mapping.direction_from_state(pad))

    def test_four_pads_route_to_four_players(self):
        im = InputManager(self.settings)
        pads = [VirtualPad(f"P{n}") for n in range(4)]
        for slot in range(4):
            im.pad_slots[slot] = 500 + slot
            im._joys[500 + slot] = pads[slot]
            im.bind_player(2 + slot, ("pad", slot))
        pads[0].set_hat((0, 1))
        pads[1].set_hat((1, 0))
        pads[2].set_button(13, 1)
        pads[3].set_axis(0, -1.0)
        im.pump_pads()
        self.assertEqual(im.controllers[2].next_direction(None, None), UP)
        self.assertEqual(im.controllers[3].next_direction(None, None), RIGHT)
        self.assertEqual(im.controllers[4].next_direction(None, None), DOWN)
        self.assertEqual(im.controllers[5].next_direction(None, None), LEFT)

    def test_disconnected_pad_yields_nothing(self):
        im = InputManager(self.settings)
        im.bind_player(2, ("pad", 0))   # slot 0 empty
        im.pump_pads()
        self.assertIsNone(im.controllers[2].next_direction(None, None))


class TestPersistence(unittest.TestCase):
    def setUp(self):
        fresh_home()

    def test_defaults_when_missing(self):
        s = SaveGame()
        self.assertEqual(s.get("wins"), 0)
        self.assertEqual(s.get("unlocked_skins"), ["solid"])

    def test_corrupted_save_recovers(self):
        s = SaveGame()
        s.set("wins", 7)
        s.save()
        with open(s._path, "w") as fh:
            fh.write("{not json!!")
        s2 = SaveGame()
        self.assertEqual(s2.get("wins"), 0)
        self.assertTrue(os.path.exists(s2._path + ".corrupt"))

    def test_record_match_updates_stats(self):
        s = SaveGame()
        result = {
            "mode": "battle", "winner_sid": 0, "winner_name": "P1",
            "winning_team": None, "team_scores": None, "duration": 42.0,
            "rankings": [
                {"sid": 0, "name": "P1", "place": 1, "alive": True,
                 "score": 120, "food": 12, "length": 15,
                 "survival_ticks": 420, "team": None, "kind": "human",
                 "reason": None},
                {"sid": 1, "name": "P2", "place": 2, "alive": False,
                 "score": 30, "food": 3, "length": 6,
                 "survival_ticks": 200, "team": None, "kind": "bot",
                 "reason": "wall"},
            ],
        }
        s.record_match(result, player_is_winner=True)
        self.assertEqual(s.get("wins"), 1)
        self.assertEqual(s.get("food_collected"), 15)
        self.assertEqual(s.get("longest_snake"), 15)
        self.assertEqual(s.get("high_scores")["battle"], 120)
        self.assertEqual(len(s.get("match_history")), 1)
        self.assertIn("first_win", s.get("achievements"))
        self.assertIn("striped", s.get("unlocked_skins"))
        # reload from disk
        s2 = SaveGame()
        self.assertEqual(s2.get("wins"), 1)

    def test_corrupted_settings_recovers(self):
        st = Settings()
        st.set("master_volume", 0.3)
        st.save()
        with open(st._path, "w") as fh:
            fh.write("### broken")
        st2 = Settings()
        self.assertEqual(st2.get("master_volume"),
                         DEFAULT_SETTINGS["master_volume"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
