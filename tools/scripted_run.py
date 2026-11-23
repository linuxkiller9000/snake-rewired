#!/usr/bin/env python3
"""Scripted end-to-end runtime test.

Boots the real game under SDL dummy drivers, injects synthetic keyboard and
FOUR virtual gamepads (six humans), drives menu -> setup -> countdown ->
gameplay -> results, and captures screenshots for visual inspection.

This exercises the full six-player input pipeline with SYNTHETIC devices;
it is not physical controller hardware verification.
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("SNAKE_REWIRED_HOME", "/tmp/sr_scripted_home")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from snake_rewired.game.app import App
from snake_rewired.game.inputman import VirtualPad
from snake_rewired.game.screens.menus import MainMenu
from snake_rewired.game.screens.setup import SetupScreen

SHOT_DIR = sys.argv[1] if len(sys.argv) > 1 else "/tmp/snake_shots"
os.makedirs(SHOT_DIR, exist_ok=True)


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k))


def shot(app, name):
    pygame.image.save(app.logical, os.path.join(SHOT_DIR, name + ".png"))
    print("shot:", name)


def frames(app, n, dt_override=None):
    for _ in range(n):
        dt = 1 / 60.0
        for ev in pygame.event.get():
            if ev.type == pygame.KEYDOWN:
                app.input.handle_keydown(pygame.key.name(ev.key))
            app.current.handle_event(ev)
        app.current.update(dt)
        app.current.draw(app.logical)
        app._present()


def main():
    pygame.init()
    app = App(headless=True)

    # Inject four virtual gamepads into slots 0-3 (P3-P6 defaults).
    pads = [VirtualPad(f"Twin USB Pad #{i + 1}") for i in range(4)]
    for slot, pad in enumerate(pads):
        app.input.pad_slots[slot] = 1000 + slot
        app.input._joys[1000 + slot] = pad

    app.push_screen(MainMenu(app))
    frames(app, 5)
    shot(app, "01_main_menu")

    # Multiplayer: Battle Arena setup
    key(pygame.K_DOWN)          # -> Multiplayer
    frames(app, 2)
    key(pygame.K_RETURN)
    frames(app, 3)
    shot(app, "02_battle_setup")

    # Device-led lobby: WASD and arrows are joined by default; the four
    # virtual pads join by pressing their primary button.
    setup = app.current
    assert isinstance(setup, SetupScreen)
    for slot in range(4):
        pygame.event.post(pygame.event.Event(
            pygame.JOYBUTTONDOWN, button=0, instance_id=1000 + slot))
    frames(app, 2)
    assert len(setup.roster) == 6, [e["device"] for e in setup.roster]
    shot(app, "03_setup_six_players")

    # Start match
    setup.focus = ("start", None)
    setup._adjust(0)
    frames(app, 2)
    from snake_rewired.game.screens.play import PlayScreen
    assert isinstance(app.current, PlayScreen), type(app.current)
    frames(app, 60)
    shot(app, "04_countdown")

    # Play ~14s: keyboard players steer with keys, pads steer via hats.
    import itertools
    key_cycle = itertools.cycle(["w", "a", "s", "d"])
    arrow_cycle = itertools.cycle(["up", "left", "down", "right"])
    hats = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    for step in range(14 * 60):
        if step % 45 == 0:
            app.input.handle_keydown(next(key_cycle))
            app.input.handle_keydown(next(arrow_cycle))
        for i, pad in enumerate(pads):
            pad.set_hat(hats[(step // 60 + i) % 4])
        frames(app, 1)
        if step == 5 * 60:
            shot(app, "05_gameplay_early")
        if step == 10 * 60:
            shot(app, "06_gameplay_late")
        if app.match_over():
            break

    # Run until match ends (all but one die).
    for _ in range(120 * 60):
        frames(app, 1)
        if app.match_over():
            break
    shot(app, "07_results_or_late")

    from snake_rewired.game.screens.play import ResultsScreen
    print("current screen:", type(app.current).__name__)
    print("match over:", app.current.match.over if hasattr(app.current, "match")
          else app.current.result is not None)
    # Garage + statistics + settings shots
    app.quit_to_menu()
    frames(app, 2)
    from snake_rewired.game.screens.menus import GarageScreen, StatsScreen, \
        SettingsScreen
    app.push_screen(GarageScreen(app)); frames(app, 10)
    shot(app, "08_garage")
    app.pop_screen()
    app.push_screen(StatsScreen(app)); frames(app, 3)
    shot(app, "09_statistics")
    app.pop_screen()
    app.push_screen(SettingsScreen(app)); frames(app, 3)
    shot(app, "10_settings")
    app.pop_screen()

    save = app.save
    print("matches recorded:", save.get("matches_played"))
    print("history:", save.get("match_history")[:2])
    print("SCRIPTED_RUN_OK")


def _match_over(self):
    s = self.current
    return getattr(s, "match", None) is not None and s.match.over


App.match_over = _match_over

if __name__ == "__main__":
    main()
