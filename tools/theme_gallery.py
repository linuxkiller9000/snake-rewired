#!/usr/bin/env python3
"""Render each arena theme mid-game to PNGs for visual inspection.

Also runs a scripted Classic Solo match (Nokia theme) with a Hard bot
driving, to verify the classic experience end to end.
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("SNAKE_REWIRED_HOME", "/tmp/sr_gallery_home")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from snake_rewired.core.match import Match, PlayerSlot
from snake_rewired.ai.brain import AIBrain
from snake_rewired.game.persistence import Settings
from snake_rewired.game.render import WorldRenderer, LOGICAL_W, LOGICAL_H

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/snake_themes"
os.makedirs(OUT, exist_ok=True)

THEMES = ["nokia", "neon", "industrial", "circuit", "minimal"]


def build_match(theme, size="medium", players=4, obstacles=None, seed=7):
    slots = [PlayerSlot(i, f"P{i+1}", kind="bot",
                        difficulty=("easy", "normal", "hard")[i % 3])
             for i in range(players)]
    m = Match("battle" if players > 1 else "classic", slots,
              arena_theme=theme, arena_size=size, obstacles=obstacles,
              seed=seed)
    for p in slots:
        m.attach_controller(p.sid, AIBrain(p.difficulty, seed=p.sid + seed))
    return m


def visuals_for(m):
    return {sid: {"color": sid, "pattern": ("solid", "striped", "dotted",
            "scaled", "circuit", "golden")[sid % 6], "head": "classic"}
            for sid in m.snakes}


def main():
    pygame.init()
    settings = Settings()
    surf = pygame.Surface((LOGICAL_W, LOGICAL_H))
    for theme in THEMES:
        m = build_match(theme)
        r = WorldRenderer(m, visuals_for(m), settings)
        # play ~12 seconds so snakes grow and eat
        for _ in range(120):
            m.update(0.1)
            if m.over:
                break
        r.draw(surf)
        pygame.image.save(surf, os.path.join(OUT, f"theme_{theme}.png"))
        print("shot:", theme, "alive:", len(m.alive_snakes()))
    # classic solo run to completion (human slot driven by a brain)
    m = Match("classic", [PlayerSlot(0, "P1")], arena_theme="nokia",
              arena_size="medium", seed=7)
    m.attach_controller(0, AIBrain("hard", seed=3))
    r = WorldRenderer(m, visuals_for(m), settings)
    ticks = 0
    while not m.over and ticks < 20000:
        m.update(0.1)
        ticks += 1
        if ticks == 200:
            r.draw(surf)
            pygame.image.save(surf, os.path.join(OUT, "classic_solo.png"))
    s = m.snakes[0]
    print(f"classic solo: over={m.over} score={s.score} food={s.food_eaten} "
          f"len={s.length} ticks={m.tick}")
    print("GALLERY_OK")


if __name__ == "__main__":
    main()
