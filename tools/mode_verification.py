#!/usr/bin/env python3
"""Scripted end-to-end verification of Score Race, Team Survival, and the
pause menu, with screenshots. Uses the real game screens headlessly."""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("SNAKE_REWIRED_HOME", "/tmp/sr_modes_home")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from snake_rewired.game.app import App
from snake_rewired.game.inputman import VirtualPad
from snake_rewired.game.screens.menus import MainMenu
from snake_rewired.game.screens.setup import SetupScreen
from snake_rewired.game.screens.play import PlayScreen, PauseScreen, ResultsScreen

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/snake_modes"
os.makedirs(OUT, exist_ok=True)


def frames(app, n):
    for _ in range(n):
        for ev in pygame.event.get():
            if ev.type == pygame.KEYDOWN:
                app.input.handle_keydown(pygame.key.name(ev.key))
            app.current.handle_event(ev)
        app.current.update(1 / 60.0)
        app.current.draw(app.logical)


def shot(app, name):
    pygame.image.save(app.logical, os.path.join(OUT, name + ".png"))
    print("shot:", name)


def start_mode(app, mode_key, slots, duration=None):
    app.push_screen(SetupScreen(app, mode_key))
    setup = app.current
    setup.roster = []
    for kind in slots:
        if kind.startswith("bot"):
            setup._join(("bot", None), difficulty=kind.split("_")[1])
        elif kind == "kb1":
            setup._join(("kb", 0))
        elif kind == "kb2":
            setup._join(("kb", 1))
        elif kind.startswith("pad"):
            setup._join(("pad", int(kind[3])))
    if duration:
        setup.duration = duration
    setup.focus = ("start", None)
    setup._start()
    assert isinstance(app.current, PlayScreen), (mode_key, type(app.current))


def main():
    pygame.init()
    app = App(headless=True)
    app.push_screen(MainMenu(app))
    frames(app, 3)

    # --- Score Race: 3 humans (kb1, kb2, pad0), 20s limit ----------------
    pads = [VirtualPad("Twin USB Pad")]
    app.input.pad_slots[0] = 900
    app.input._joys[900] = pads[0]
    start_mode(app, "score_race", ["kb1", "kb2", "pad0"], duration=20)
    frames(app, 4 * 60)  # countdown + 1s
    pads[0].set_hat((0, 1))
    frames(app, 8 * 60)
    shot(app, "20_score_race_mid")
    # run out the clock
    for _ in range(60 * 60):
        frames(app, 1)
        if app.match_over():
            break
    assert isinstance(app.current, ResultsScreen), type(app.current)
    shot(app, "21_score_race_results")
    print("score race winner:", app.current.result["winner_name"],
          "top:", app.current.result["rankings"][0]["score"])

    # --- pause menu evidence ---------------------------------------------
    app.quit_to_menu(); frames(app, 2)
    start_mode(app, "battle", ["kb1", "bot_normal"], duration=None)
    frames(app, 4 * 60 + 30)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
    frames(app, 3)
    assert isinstance(app.current, PauseScreen), type(app.current)
    shot(app, "22_pause_menu")
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    frames(app, 3)  # resume
    assert isinstance(app.current, PlayScreen), type(app.current)

    # --- Team Survival: 2v2, bots on team 2 --------------------------------
    app.quit_to_menu(); frames(app, 2)
    start_mode(app, "team_survival", ["kb1", "bot_hard", "kb2", "bot_hard"],
               duration=90)
    # assign teams: slots 0,2 -> team 0; slots 1,3 -> team 1 (default i%2)
    frames(app, 4 * 60)
    for _ in range(120 * 60):
        frames(app, 1)
        if app.match_over():
            break
    assert isinstance(app.current, ResultsScreen), type(app.current)
    shot(app, "23_team_survival_results")
    print("team survival winning team:", app.current.result["winning_team"],
          "team scores:", app.current.result["team_scores"])
    print("MODES_OK")


def _match_over(self):
    s = self.current
    return getattr(s, "match", None) is not None and s.match.over


App.match_over = _match_over

if __name__ == "__main__":
    main()
