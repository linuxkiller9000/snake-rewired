"""Main menu, statistics, credits, garage (customization), settings."""

import pygame

from ...core.modes import MODES
from ...core.arena import THEMES, SIZES
from ..render import LOGICAL_W, LOGICAL_H, player_color, player_color_name
from .base import (Screen, MenuScreen, font, draw_panel, wrap_text,
                   ACCENT, TEXT, DIM, BG)
from .setup import SetupScreen


class MainMenu(MenuScreen):
    title = "SNAKE: REWIRED"
    subtitle = "Six snakes. One arena. No mercy."

    def _build(self):
        self.add("Play: Classic",
                 lambda: self.app.show_setup("classic"))
        self.add("Multiplayer: Battle Arena",
                 lambda: self.app.show_setup("battle"))
        self.add("Score Race",
                 lambda: self.app.show_setup("score_race"))
        self.add("Team Survival",
                 lambda: self.app.show_setup("team_survival"))
        self.add("Garage: Snake Customization",
                 lambda: self.app.push_screen(GarageScreen(self.app)))
        self.add("Statistics",
                 lambda: self.app.push_screen(StatsScreen(self.app)))
        self.add("Settings",
                 lambda: self.app.push_screen(SettingsScreen(self.app)))
        self.add("Credits",
                 lambda: self.app.push_screen(CreditsScreen(self.app)))
        self.add("Exit", self.app.quit)

    DESCRIPTIONS = {
        "Play: Classic": "Faithful Nokia-style Snake: play alone or add bots, growing speed, high-score chase.",
        "Multiplayer: Battle Arena": "Up to 6 snakes share one arena: last snake slithering wins.",
        "Score Race": "Most food before the clock runs out takes the match.",
        "Team Survival": "Two teams, shared score: keep your teammates alive.",
        "Garage: Snake Customization": "Pick each player's color, pattern and head.",
        "Statistics": "Your matches, wins, food and best scores.",
        "Settings": "Display, audio, controls and accessibility options.",
        "Credits": "Who made this and with what.",
        "Exit": "Close the game.",
    }

    def draw(self, surf):
        super().draw(surf)
        # one-line description of the highlighted item
        label = self.items[self.index][0] if self.items else ""
        desc = self.DESCRIPTIONS.get(label)
        if desc:
            d = font(24).render(desc, True, DIM)
            surf.blit(d, d.get_rect(center=(LOGICAL_W // 2, LOGICAL_H - 56)))
        # little snake logo wiggle
        t = pygame.time.get_ticks() // 90
        for i in range(10):
            x = LOGICAL_W // 2 - 150 + i * 30
            y = 128 + int(8 * ((t + i) % 4 - 1.5))
            c = player_color(i % 6)
            pygame.draw.rect(surf, c, (x, y, 24, 24), border_radius=6)


class StatsScreen(Screen):
    def __init__(self, app):
        self.app = app

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (
                pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            self.app.pop_screen()
        elif ev.type == pygame.JOYBUTTONDOWN:
            self.app.pop_screen()

    def draw(self, surf):
        surf.fill(BG)
        t = font(56).render("STATISTICS", True, ACCENT)
        surf.blit(t, t.get_rect(center=(LOGICAL_W // 2, 50)))
        s = self.app.save
        panel = pygame.Rect(80, 100, 560, 560)
        draw_panel(surf, panel)
        rows = [
            ("Matches played", s.get("matches_played", 0)),
            ("Wins", s.get("wins", 0)),
            ("Losses", s.get("losses", 0)),
            ("Food collected", s.get("food_collected", 0)),
            ("Longest snake", s.get("longest_snake", 0)),
            ("Best survival", f"{s.get('best_survival_seconds', 0.0):.1f}s"),
            ("Total play time", f"{s.get('total_play_seconds', 0.0):.0f}s"),
        ]
        y = panel.y + 22
        for label, value in rows:
            surf.blit(font(30).render(label, True, TEXT), (panel.x + 24, y))
            v = font(30).render(str(value), True, ACCENT)
            surf.blit(v, (panel.right - 24 - v.get_width(), y))
            y += 38
        y += 10
        surf.blit(font(32).render("High scores", True, (240, 220, 140)),
                  (panel.x + 24, y))
        y += 38
        hs = s.get("high_scores", {})
        for mode in MODES:
            if mode in hs:
                surf.blit(font(28).render(MODES[mode].title, True, TEXT),
                          (panel.x + 24, y))
                v = font(28).render(str(hs[mode]), True, ACCENT)
                surf.blit(v, (panel.right - 24 - v.get_width(), y))
                y += 32
        right = pygame.Rect(700, 100, 586, 560)
        draw_panel(surf, right)
        surf.blit(font(32).render("Achievements", True, (240, 220, 140)),
                  (right.x + 24, right.y + 18))
        y = right.y + 56
        ach = s.get("achievements", {})
        names = {"first_match": "First Match", "first_win": "First Win",
                 "champion": "Champion (10 wins)", "glutton": "Glutton (100 food)",
                 "feast": "Feast (500 food)", "centipede": "Centipede (len 25)",
                 "survivor": "Survivor (120s)", "team_player": "Team Player"}
        for key, label in names.items():
            got = key in ach
            color = ACCENT if got else DIM
            mark = "[x]" if got else "[ ]"
            surf.blit(font(28).render(f"{mark} {label}", True, color),
                      (right.x + 24, y))
            y += 32
        y += 12
        surf.blit(font(32).render("Recent matches", True, (240, 220, 140)),
                  (right.x + 24, y))
        y += 38
        for entry in s.get("match_history", [])[:7]:
            line = (f"{MODES.get(entry['mode'], MODES['classic']).title:<14} "
                    f"winner: {entry.get('winner') or '-':<10} "
                    f"top {entry.get('top_score', 0)}")
            surf.blit(font(24).render(line, True, TEXT), (right.x + 24, y))
            y += 28
        foot = font(24).render("Esc: back", True, DIM)
        surf.blit(foot, foot.get_rect(center=(LOGICAL_W // 2, LOGICAL_H - 24)))


class CreditsScreen(Screen):
    def __init__(self, app):
        self.app = app

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN or ev.type == pygame.JOYBUTTONDOWN:
            self.app.pop_screen()

    def draw(self, surf):
        surf.fill(BG)
        t = font(56).render("CREDITS", True, ACCENT)
        surf.blit(t, t.get_rect(center=(LOGICAL_W // 2, 60)))
        lines = [
            "SNAKE: REWIRED",
            "",
            "A modern local-multiplayer evolution of classic Snake.",
            "",
            "Design, code, art and sound: Instinct game-dev agent",
            "Engine: Python 3 + pygame-ce",
            "All artwork and audio are original and procedurally generated.",
            "No copyrighted Nokia assets are used.",
            "",
            "Thanks for playing.",
        ]
        y = 160
        for i, line in enumerate(lines):
            f = font(44 if i == 0 else 30)
            color = ACCENT if i == 0 else TEXT
            label = f.render(line, True, color)
            surf.blit(label, label.get_rect(center=(LOGICAL_W // 2, y)))
            y += 52 if i == 0 else 36
        foot = font(24).render("Any key: back", True, DIM)
        surf.blit(foot, foot.get_rect(center=(LOGICAL_W // 2, LOGICAL_H - 24)))


PATTERNS = ["solid", "striped", "dotted", "scaled", "circuit", "golden"]
HEADS = ["classic", "visor", "arrow"]


class GarageScreen(Screen):
    """Per-player color / pattern / head customization with live preview."""

    def __init__(self, app):
        self.app = app
        self.player = 0
        self.option = 0  # 0 color, 1 pattern, 2 head
        self.anim = 0.0

    def _cfg(self):
        players = self.app.settings.get("players")
        return players[self.player]

    def _save_cfg(self, key, value):
        players = list(self.app.settings.get("players"))
        cfg = dict(players[self.player])
        cfg[key] = value
        players[self.player] = cfg
        self.app.settings.set("players", players)
        self.app.settings.save()

    def _unlocked(self, pattern):
        return pattern in self.app.save.get("unlocked_skins", ["solid"])

    def handle_event(self, ev):
        if ev.type != pygame.KEYDOWN:
            return
        k = ev.key
        if k in (pygame.K_ESCAPE,):
            self.app.pop_screen()
        elif k in (pygame.K_TAB, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            pass
        elif k in (pygame.K_q, pygame.K_e):
            delta = -1 if k == pygame.K_q else 1
            self.player = (self.player + delta) % 6
            self.app.audio.play("menu_move")
        elif k in (pygame.K_UP, pygame.K_w):
            self.option = (self.option - 1) % 3
            self.app.audio.play("menu_move")
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.option = (self.option + 1) % 3
            self.app.audio.play("menu_move")
        elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            delta = -1 if k in (pygame.K_LEFT, pygame.K_a) else 1
            cfg = self._cfg()
            if self.option == 0:
                cfg["color"] = (cfg.get("color", self.player) + delta) % 6
                self._save_cfg("color", cfg["color"])
            elif self.option == 1:
                cur = cfg.get("pattern", "solid")
                idx = PATTERNS.index(cur) if cur in PATTERNS else 0
                for step in range(1, len(PATTERNS) + 1):
                    cand = PATTERNS[(idx + delta * step) % len(PATTERNS)]
                    if self._unlocked(cand):
                        self._save_cfg("pattern", cand)
                        break
            else:
                cur = cfg.get("head", "classic")
                idx = HEADS.index(cur) if cur in HEADS else 0
                for step in range(1, len(HEADS) + 1):
                    cand = HEADS[(idx + delta * step) % len(HEADS)]
                    if cand != "visor" or self._unlocked("visor"):
                        self._save_cfg("head", cand)
                        break
                else:
                    self.app.toast("Visor head unlocks with the Survivor "
                                   "achievement")
            self.app.audio.play("menu_move")

    def update(self, dt):
        self.anim += dt

    def draw(self, surf):
        surf.fill(BG)
        t = font(56).render("GARAGE", True, ACCENT)
        surf.blit(t, t.get_rect(center=(LOGICAL_W // 2, 50)))
        sub = font(26).render("Q/E: choose player   Up/Down: option   "
                              "Left/Right: change   Esc: back", True, DIM)
        surf.blit(sub, sub.get_rect(center=(LOGICAL_W // 2, 92)))
        cfg = self._cfg()
        # player chips
        for i in range(6):
            chip = pygame.Rect(LOGICAL_W // 2 - 260 + i * 90, 120, 70, 44)
            sel = i == self.player
            pygame.draw.rect(surf, player_color(i if i != self.player
                                                else cfg.get("color", i)),
                             chip, border_radius=8)
            pygame.draw.rect(surf, (250, 250, 250) if sel else (60, 60, 70),
                             chip, 3 if sel else 1, border_radius=8)
            label = font(28).render(f"P{i + 1}", True, (15, 15, 20))
            surf.blit(label, label.get_rect(center=chip.center))
        panel = pygame.Rect(LOGICAL_W // 2 - 320, 190, 640, 400)
        draw_panel(surf, panel)
        rows = [("Color", player_color_name(cfg.get("color", self.player))),
                ("Pattern", cfg.get("pattern", "solid").title()
                 + ("" if self._unlocked(cfg.get("pattern", "solid"))
                    else " (locked)")),
                ("Head", cfg.get("head", "classic").title())]
        y = panel.y + 30
        for i, (label, value) in enumerate(rows):
            sel = i == self.option
            f = font(36 if sel else 30)
            color = ACCENT if sel else TEXT
            surf.blit(f.render(label, True, color), (panel.x + 30, y))
            v = f.render(f"< {value} >", True, color if sel else DIM)
            surf.blit(v, (panel.right - 30 - v.get_width(), y))
            y += 56
        # live preview: animated snake sample
        import math
        from ..render import draw_snake, SnakeSkin, Layout
        from ...core.arena import Arena
        skin = SnakeSkin(cfg.get("color", self.player),
                         cfg.get("pattern", "solid"), cfg.get("head", "classic"))
        base_x = panel.x + 110
        base_y = panel.bottom - 110
        cells = []
        for i in range(9):
            x = base_x + (8 - i) * 34
            ypos = base_y + int(14 * math.sin(self.anim * 3 + i * 0.7))
            cells.append((x, ypos))
        fake_layout = Layout(Arena("neon", "medium"))
        fake_layout.cell = 26
        draw_snake(surf, fake_layout, cells, skin, self.player + 1)
        hint = font(24).render(
            "Locked skins come from achievements (win matches, eat food, "
            "survive long).", True, DIM)
        surf.blit(hint, hint.get_rect(center=(LOGICAL_W // 2,
                                              panel.bottom + 30)))


class SettingsScreen(Screen):
    ROWS = [
        ("master_volume", "Master volume", "vol"),
        ("music_volume", "Music volume", "vol"),
        ("sfx_volume", "Effects volume", "vol"),
        ("muted", "Mute all", "bool"),
        ("fullscreen", "Fullscreen", "bool"),
        ("vsync", "VSync", "bool"),
        ("show_grid", "Show grid", "bool"),
        ("high_contrast", "High contrast snakes", "bool"),
        ("remap1", "Remap Player 1 keys", "remap"),
        ("remap2", "Remap Player 2 keys", "remap"),
        ("pad_hat", "Controller D-pad (hat)", "bool"),
        ("pad_stick", "Controller analog stick", "bool"),
        ("remap_pad", "Remap controller buttons", "remap_pad"),
        ("save", "Save settings", "action"),
    ]

    def __init__(self, app):
        self.app = app
        self.index = 0
        self.capture = None  # (player, action) waiting for a key

    def _value(self, key):
        if key == "remap1":
            m = self.app.settings.get("keys_p1", {})
            return " ".join(str(m.get(a, "-")).upper() for a in
                            ("up", "left", "down", "right"))
        if key == "remap2":
            m = self.app.settings.get("keys_p2", {})
            return " ".join(str(m.get(a, "-")).upper() for a in
                            ("up", "left", "down", "right"))
        if key == "remap_pad":
            m = self.app.settings.get("pad_buttons", {})
            return " ".join(f"{a[0].upper()}:{m.get(a, '-')}" for a in
                            ("up", "left", "down", "right"))
        if key == "pad_hat":
            return "On" if self.app.settings.get("pad_use_hat", True) else "Off"
        if key == "pad_stick":
            return "On" if self.app.settings.get("pad_use_stick", True) else "Off"
        v = self.app.settings.get(key)
        if key.endswith("volume"):
            return f"{int(float(v) * 100)}%"
        if isinstance(v, bool):
            return "On" if v else "Off"
        return str(v)

    def _adjust(self, delta):
        key, _label, kind = self.ROWS[self.index]
        s = self.app.settings
        if kind == "vol":
            s.set(key, round(min(1.0, max(0.0, float(s.get(key, 0.5))
                                            + 0.1 * delta)), 2))
            self.app.audio.apply_volumes()
            self.app.audio.play("menu_move")
        elif kind == "bool":
            if key == "pad_hat":
                s.set("pad_use_hat", not s.get("pad_use_hat", True))
            elif key == "pad_stick":
                s.set("pad_use_stick", not s.get("pad_use_stick", True))
            else:
                s.set(key, not s.get(key))
            self.app.audio.apply_volumes()
            if key in ("fullscreen", "vsync"):
                self.app.apply_display_mode()
            self.app.audio.play("menu_move")

    def handle_event(self, ev):
        if self.capture is not None:
            if self.capture[0] == "pad":
                if ev.type == pygame.JOYBUTTONDOWN:
                    action = self.capture[1]
                    buttons = dict(self.app.settings.get("pad_buttons", {}))
                    for act, idx in list(buttons.items()):
                        if idx == ev.button:
                            del buttons[act]
                    buttons[action] = ev.button
                    self.app.settings.set("pad_buttons", buttons)
                    self.app.settings.save()
                    self.app.toast(f"Pad {action} -> button {ev.button}")
                    if getattr(self, "_capture_queue", None):
                        self.capture = self._capture_queue.pop(0)
                    else:
                        self.capture = None
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    self.capture = None
                    self._capture_queue = []
                return
            if ev.type == pygame.KEYDOWN:
                player, action = self.capture
                name = pygame.key.name(ev.key)
                self.app.input.keyboard.remap(player, action, name)
                self.app.settings.save()
                self.app.toast(f"P{player + 1} {action} -> {name}")
                if getattr(self, "_capture_queue", None):
                    self.capture = self._capture_queue.pop(0)
                else:
                    self.capture = None
            return
        if ev.type != pygame.KEYDOWN:
            return
        k = ev.key
        if k == pygame.K_ESCAPE:
            self.app.settings.save()
            self.app.pop_screen()
        elif k in (pygame.K_UP, pygame.K_w):
            self.index = (self.index - 1) % len(self.ROWS)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.index = (self.index + 1) % len(self.ROWS)
        elif k in (pygame.K_LEFT, pygame.K_a):
            self._adjust(-1)
        elif k in (pygame.K_RIGHT, pygame.K_d):
            self._adjust(1)
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            key, _label, kind = self.ROWS[self.index]
            if kind == "remap":
                player = 0 if key == "remap1" else 1
                self.capture = (player, "up")
                self.app.toast(f"Press key for P{player + 1} UP "
                               f"(then down/left/right follow)")
                self._capture_queue = [(player, a) for a in
                                       ("down", "left", "right")]
            elif kind == "remap_pad":
                self.capture = ("pad", "up")
                self.app.toast("Press a controller button for UP "
                               "(then down/left/right; Esc cancels)")
                self._capture_queue = [("pad", a) for a in
                                       ("down", "left", "right")]
            elif kind == "action":
                self.app.settings.save()
                self.app.toast("Settings saved")
            else:
                self._adjust(1)

    def draw(self, surf):
        surf.fill(BG)
        t = font(56).render("SETTINGS", True, ACCENT)
        surf.blit(t, t.get_rect(center=(LOGICAL_W // 2, 54)))
        panel = pygame.Rect(LOGICAL_W // 2 - 380, 100, 760, 620)
        draw_panel(surf, panel)
        y = panel.y + 20
        for i, (key, label, kind) in enumerate(self.ROWS):
            sel = i == self.index
            if sel:
                hl = pygame.Rect(panel.x + 12, y - 4, panel.width - 24, 40)
                pygame.draw.rect(surf, (44, 60, 76), hl, border_radius=6)
            f = font(32 if sel else 28)
            surf.blit(f.render(label, True, ACCENT if sel else TEXT),
                      (panel.x + 26, y))
            if kind != "action":
                v = f.render(f"< {self._value(key)} >", True,
                             TEXT if sel else DIM)
                surf.blit(v, (panel.right - 26 - v.get_width(), y))
            y += 44
        if self.capture is not None:
            who, action = self.capture
            what = "a controller button" if who == "pad" else f"a key for P{who + 1}"
            msg = font(32).render(
                f"Press {what} for {action.upper()}...",
                True, (255, 230, 140))
            surf.blit(msg, msg.get_rect(center=(LOGICAL_W // 2, 742)))
