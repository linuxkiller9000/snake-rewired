#!/usr/bin/env python3
"""SNAKE: REWIRED entry point."""
import os
import sys

# Headless smoke-test support: SNAKE_HEADLESS=1 uses SDL dummy drivers.
if os.environ.get("SNAKE_HEADLESS"):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from snake_rewired.game.app import App
from snake_rewired.game.screens.menus import MainMenu


def main():
    pygame.init()
    app = App()
    app.push_screen(MainMenu(app))
    max_frames = None
    if os.environ.get("SNAKE_FRAMES"):
        max_frames = int(os.environ["SNAKE_FRAMES"])
    app.run(max_frames=max_frames)
    pygame.quit()


if __name__ == "__main__":
    main()
