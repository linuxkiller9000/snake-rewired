"""Application shell: window, main loop, screen stack, match lifecycle."""

import os
import sys

import pygame

from .persistence import Settings, SaveGame
from .inputman import InputManager
from .audio import AudioManager
from .render import LOGICAL_W, LOGICAL_H
from ..core.match import Match


class App:
    def __init__(self, headless=False):
        self.settings = Settings()
        self.save = SaveGame()
        self.input = InputManager(self.settings)
        self.audio = AudioManager(self.settings)
        self.running = True
        self.screens = []
        self.toasts = []
        self._last_match_config = None
        self.headless = headless

        flags = pygame.RESIZABLE | pygame.SCALED
        if self.settings.get("fullscreen"):
            flags |= pygame.FULLSCREEN
        vsync = 1 if self.settings.get("vsync") else 0
        try:
            self.window = pygame.display.set_mode(
                (LOGICAL_W, LOGICAL_H), flags, vsync=vsync)
        except pygame.error:
            self.window = pygame.display.set_mode((LOGICAL_W, LOGICAL_H),
                                                  flags)
        pygame.display.set_caption("SNAKE: REWIRED")
        self.logical = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.clock = pygame.time.Clock()
        self.audio.init(pygame)
        self.input.init_pygame(pygame)
        self.audio.start_music()

    # -- display ------------------------------------------------------------
    def apply_display_mode(self):
        flags = pygame.RESIZABLE | pygame.SCALED
        if self.settings.get("fullscreen"):
            flags |= pygame.FULLSCREEN
        vsync = 1 if self.settings.get("vsync") else 0
        try:
            self.window = pygame.display.set_mode(
                (LOGICAL_W, LOGICAL_H), flags, vsync=vsync)
        except pygame.error:
            self.window = pygame.display.set_mode((LOGICAL_W, LOGICAL_H),
                                                  flags)

    # -- screens --------------------------------------------------------------
    def push_screen(self, screen):
        self.screens.append(screen)
        screen.on_enter()

    def pop_screen(self):
        if len(self.screens) > 1:
            self.screens.pop()

    def switch_screen(self, screen):
        self.screens = [screen]
        screen.on_enter()

    @property
    def current(self):
        return self.screens[-1]

    def toast(self, text):
        from .screens.base import Toast
        self.toasts.append(Toast(text))

    def quit(self):
        self.running = False

    # -- match lifecycle ------------------------------------------------------
    def show_setup(self, mode_key):
        from .screens.setup import SetupScreen
        self.push_screen(SetupScreen(self, mode_key))

    def start_match(self, mode_key, players, visuals, controllers, *,
                    theme, size, speed, duration, obstacles):
        from .screens.play import PlayScreen
        pattern = None
        if not obstacles:
            pattern = "none"
        match = Match(mode_key, players, arena_theme=theme, arena_size=size,
                      speed=speed, duration=duration, obstacles=pattern)
        self._last_match_config = (mode_key, players, visuals, controllers,
                                   dict(theme=theme, size=size, speed=speed,
                                        duration=duration, obstacles=obstacles))
        # Clear any stale human bindings from previous matches.
        for idx in list(self.input.player_devices):
            if idx >= len(players):
                self.input.unbind_player(idx)
        self.switch_screen(PlayScreen(self, match, visuals, controllers))

    def rematch(self):
        if self._last_match_config is None:
            self.quit_to_menu()
            return
        mode_key, players, visuals, controllers, kw = self._last_match_config
        self.start_match(mode_key, players, visuals, controllers, **kw)

    def quit_to_menu(self):
        from .screens.menus import MainMenu
        self.switch_screen(MainMenu(self))

    def finish_match(self, match, result):
        # Record stats: the human with the best rank decides win/loss.
        humans = [r for r in result["rankings"] if r["kind"] == "human"]
        won = bool(humans) and (
            (match.mode.teams and result.get("winning_team") is not None and
             any(r["team"] == result["winning_team"] for r in humans))
            or (not match.mode.teams and humans[0]["place"] == 1))
        self.save.record_match(result, won)
        self.save.save()

    # -- main loop --------------------------------------------------------------
    def run(self, max_frames=None):
        frames = 0
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.1)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                    continue
                hot = self.input.handle_hotplug(ev)
                if hot:
                    kind, _ = hot
                    self.toast(f"Controller {kind}")
                    continue
                if ev.type == pygame.KEYDOWN:
                    # gameplay input first, then the active screen
                    self.input.handle_keydown(pygame.key.name(ev.key))
                self.current.handle_event(ev)
            self.current.update(dt)
            self.current.draw(self.logical)
            for t in self.toasts:
                t.draw(self.logical)
            self.toasts = [t for t in self.toasts if (t.remaining - dt) > 0]
            for t in self.toasts:
                t.remaining -= dt
            self._present()
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
        self.settings.save()
        self.save.save()

    def _present(self):
        w, h = self.window.get_size()
        if (w, h) == (LOGICAL_W, LOGICAL_H):
            self.window.blit(self.logical, (0, 0))
        else:
            scaled = pygame.transform.smoothscale(self.logical, (w, h))
            self.window.blit(scaled, (0, 0))
        pygame.display.flip()
