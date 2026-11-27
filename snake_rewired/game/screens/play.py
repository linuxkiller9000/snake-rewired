"""Gameplay screen: countdown, live match, pause, elimination feed, results."""

import pygame

from ...core.match import Match
from ...ai.brain import AIBrain
from ..render import WorldRenderer, LOGICAL_W, LOGICAL_H
from .base import Screen, MenuScreen, font, draw_panel, ACCENT, TEXT, DIM, BG


class Countdown:
    DUR = 3.0

    def __init__(self):
        self.t = 0.0
        self.last_step = 4

    def update(self, dt, audio):
        self.t += dt
        step = 3 - int(self.t)
        if step != self.last_step and step >= 0:
            audio.play("countdown" if step > 0 else "go")
            self.last_step = step
        return self.t >= self.DUR

    def label(self):
        step = 3 - int(self.t)
        return str(step) if step > 0 else "GO!"


class PlayScreen(Screen):
    def __init__(self, app, match, visuals, controllers):
        self.app = app
        self.match = match
        self.renderer = WorldRenderer(match, visuals, app.settings)
        self.countdown = Countdown()
        self.started = False
        self.paused = False
        self.elim_msgs = []   # (text, ttl)
        self.result_screen = None
        for sid, p in match.players.items():
            if p.kind == "bot":
                match.attach_controller(sid, AIBrain(p.difficulty,
                                                     seed=1000 + sid))
            else:
                match.attach_controller(sid, controllers[sid])

    # ------------------------------------------------------------------
    def handle_event(self, ev):
        if self.match.over:
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_p) and self.started:
                self.paused = not self.paused
                self.app.audio.play("pause")
                if self.paused:
                    self.app.push_screen(PauseScreen(self.app, self))
        elif ev.type == pygame.JOYBUTTONDOWN and ev.button in (6, 7, 9):
            if self.started and not self.match.over:
                self.paused = not self.paused
                self.app.audio.play("pause")
                if self.paused:
                    self.app.push_screen(PauseScreen(self.app, self))

    def update(self, dt):
        if self.paused or self.match.over:
            return
        if not self.started:
            if self.countdown.update(dt, self.app.audio):
                self.started = True
            return
        self.app.input.pump_pads()
        events = self.match.update(dt)
        for ev in events:
            kind = ev[0]
            if kind == "eat":
                _, snake, item = ev
                sfx = {"normal": "food", "bonus": "bonus", "golden": "golden",
                       "speed": "speed", "slow": "slow"}.get(item.kind, "food")
                self.app.audio.play(sfx)
            elif kind == "death":
                _, snake, reason = ev
                self.app.audio.play("death")
                self.elim_msgs.append(
                    (f"{snake.name} eliminated "
                     f"({reason})!", 2.6))
            elif kind == "match_over":
                self.app.audio.play("victory")
                self._finish(ev[1])
        self.elim_msgs = [(t, ttl - dt) for t, ttl in self.elim_msgs
                          if ttl - dt > 0]

    def _finish(self, result):
        prev_best = self.app.save.get("high_scores", {}).get(
            result.get("mode", ""), 0)
        self.app.finish_match(self.match, result)
        self.app.switch_screen(ResultsScreen(self.app, self.match, result,
                                             self.renderer, prev_best))

    # ------------------------------------------------------------------
    def draw(self, surf):
        self.renderer.draw(surf)
        arect = self.renderer.layout.rect
        y = arect.y + 8
        for text, _ttl in self.elim_msgs[:3]:
            label = font(24).render(text, True, (255, 150, 150))
            bg = label.get_rect().inflate(16, 6)
            bg.topright = (arect.right - 8, y)
            shade = pygame.Surface(bg.size, pygame.SRCALPHA)
            shade.fill((20, 10, 10, 170))
            surf.blit(shade, bg)
            surf.blit(label, (bg.x + 8, bg.y + 3))
            y += 30
        if self.started and not self.match.over:
            hint = font(20).render("Esc: pause", True, (150, 148, 155))
            surf.blit(hint, (arect.x + 10, arect.bottom - 26))
        if not self.started:
            dim = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 130))
            surf.blit(dim, (0, 0))
            big = font(160).render(self.countdown.label(), True, ACCENT)
            surf.blit(big, big.get_rect(center=(LOGICAL_W // 2,
                                                LOGICAL_H // 2)))


class PauseScreen(MenuScreen):
    title = "PAUSED"

    def __init__(self, app, play_screen):
        self.play_screen = play_screen
        super().__init__(app)

    def _build(self):
        self.add("Resume", self._resume)
        self.add("Restart match", self._restart)
        self.add("Quit to menu", self._quit)

    def _resume(self):
        self.play_screen.paused = False
        self.app.pop_screen()

    def back(self):
        self._resume()

    def _restart(self):
        self.play_screen.paused = False
        self.app.pop_screen()
        self.app.rematch()

    def _quit(self):
        self.play_screen.paused = False
        self.app.quit_to_menu()


class ResultsScreen(Screen):
    def __init__(self, app, match, result, renderer, prev_best=0):
        self.app = app
        self.match = match
        self.result = result
        self.renderer = renderer
        self.prev_best = prev_best

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_r,):
                self.app.rematch()
            elif ev.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                self.app.quit_to_menu()
        elif ev.type == pygame.JOYBUTTONDOWN and ev.button in (0, 1, 9):
            self.app.quit_to_menu()

    def draw(self, surf):
        surf.fill(BG)
        res = self.result
        solo = len(res["rankings"]) == 1
        if solo:
            # A solo run has no opponent to beat: say what happened.
            headline = "GAME OVER"
        elif self.match.mode.teams and res.get("winning_team") is not None:
            headline = f"TEAM {res['winning_team'] + 1} WINS!"
        elif res.get("winner_name"):
            headline = f"{res['winner_name']} WINS!"
        else:
            headline = "MATCH OVER"
        t = font(84).render(headline, True, ACCENT)
        surf.blit(t, t.get_rect(center=(LOGICAL_W // 2, 70)))
        top_score = max((r["score"] for r in res["rankings"]), default=0)
        if top_score > self.prev_best and top_score > 0:
            best_part, ncolor = f"New best score: {top_score}!", (240, 220, 140)
        elif self.prev_best > 0:
            best_part, ncolor = f"Best: {self.prev_best}", DIM
        else:
            best_part, ncolor = None, DIM
        secs = int(res.get("duration", 0))
        note = "   ·   ".join(([best_part] if best_part else []) +
                           [f"Time {secs // 60}:{secs % 60:02d}"])
        nt = font(28).render(note, True, ncolor)
        surf.blit(nt, nt.get_rect(center=(LOGICAL_W // 2, 122)))
        # Panel height fits the rows instead of a fixed tall empty box.
        n_rows = len(res["rankings"])
        n_team = len(res.get("team_scores") or {})
        panel_h = 54 + n_rows * 38 + (8 + n_team * 32 if n_team else 0) + 16
        panel = pygame.Rect(LOGICAL_W // 2 - 430, 150, 860, panel_h)
        draw_panel(surf, panel)
        header = font(28).render(
            f"{'#':<3} {'Player':<18} {'Score':>7} {'Food':>6} "
            f"{'Length':>7} {'Time':>7}", True, DIM)
        surf.blit(header, (panel.x + 30, panel.y + 18))
        y = panel.y + 54
        for row in res["rankings"]:
            alive = row["alive"]
            color = (240, 240, 245) if alive else (150, 148, 155)
            name = row["name"] + (f" [T{row['team'] + 1}]"
                                  if row["team"] is not None else "")
            secs = row["survival_ticks"] / 10.0
            line = (f"{row['place']:<3} {name:<18} {row['score']:>7} "
                    f"{row['food']:>6} {row['length']:>7} {secs:>6.1f}s")
            label = font(30).render(line, True, color)
            if not alive:
                label.set_alpha(170)
            surf.blit(label, (panel.x + 30, y))
            y += 38
        ts = res.get("team_scores")
        if ts:
            y += 8
            for team in sorted(ts):
                label = font(30).render(f"Team {team + 1}: {ts[team]} points",
                                        True, (240, 220, 140))
                surf.blit(label, (panel.x + 30, y))
                y += 32
        foot = font(26).render("R: rematch    Enter: menu", True, DIM)
        surf.blit(foot, foot.get_rect(center=(LOGICAL_W // 2, LOGICAL_H - 30)))
