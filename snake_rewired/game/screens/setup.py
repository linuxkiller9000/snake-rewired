"""Match setup: mode options plus a device-led lobby.

Players join by pressing a key on the device they will use: W joins the
WASD player (S leaves), Up joins the arrow-keys player (Down leaves), and
a controller's primary button joins that pad (secondary button leaves).
B adds a bot, X removes the most recent bot. Tab moves between option
rows, Left/Right changes values, Enter starts.
"""

import pygame

from ...core.modes import MODES, SPEEDS, DURATION_OPTIONS
from ...core.arena import THEMES, SIZES
from ..render import LOGICAL_W, LOGICAL_H, player_color
from .base import Screen, font, draw_panel, ACCENT, TEXT, DIM, BG

BOT_DIFFS = ("easy", "normal", "hard")


class SetupScreen(Screen):
    def __init__(self, app, mode_key):
        self.app = app
        self.mode = MODES[mode_key]
        s = app.settings
        self.theme = s.get("arena_theme", "neon")
        self.size = s.get("arena_size", "medium")
        self.speed = s.get("speed", "normal")
        self.duration = s.get("match_duration", self.mode.default_duration)
        self.obstacles = bool(s.get("obstacles", True))
        # Roster entries: {"device": ("kb",0)/("kb",1)/("pad",n)/("bot",None),
        #                  "difficulty": str (bots), "team": int}
        self.roster = []
        # Focus order: option rows, then roster rows, then START.
        self.focus = ("start", None)
        self.focus_rows = [("start", None)]
        self._join(("kb", 0))
        if self.mode.min_players > 1:
            self._join(("kb", 1))
        self._rebuild_focus()

    # -- roster ------------------------------------------------------------
    def _joined(self, device):
        return any(e["device"] == device for e in self.roster)

    def _join(self, device, difficulty="normal"):
        if device[0] != "bot" and self._joined(device):
            return False
        if len(self.roster) >= self.mode.max_players:
            return False
        if device[0] == "bot" and not self.mode.allow_bots:
            return False
        if device[0] == "kb" and device[1] == 1 and self.mode.max_players < 2:
            return False
        self.roster.append({"device": device, "difficulty": difficulty,
                            "team": len(self.roster) % 2})
        self._rebuild_focus()
        self.app.audio.play("menu_select")
        return True

    def _leave(self, device):
        for i, e in enumerate(self.roster):
            if e["device"] == device:
                del self.roster[i]
                self._rebuild_focus()
                self.app.audio.play("menu_move")
                return True
        return False

    def _add_bot(self):
        return self._join(("bot", None), difficulty="normal")

    def _remove_bot(self):
        for i in range(len(self.roster) - 1, -1, -1):
            if self.roster[i]["device"][0] == "bot":
                del self.roster[i]
                self._rebuild_focus()
                self.app.audio.play("menu_move")
                return True
        return False

    def _kb_join_key(self, player_index, action):
        mapping = self.app.settings.get(
            "keys_p1" if player_index == 0 else "keys_p2", {})
        return mapping.get(action)

    def _handle_lobby_key(self, key_name):
        """Device-led join/leave. Returns True when the key was consumed."""
        pairs = ((0, ("kb", 0)), (1, ("kb", 1)))
        for player_index, device in pairs:
            if key_name == self._kb_join_key(player_index, "up"):
                if not self._joined(device):
                    if device[1] == 1 and self.mode.max_players < 2:
                        return True
                    if not self._join(device):
                        self.app.toast("Lobby is full")
                return True
            if key_name == self._kb_join_key(player_index, "down"):
                self._leave(device)
                return True
        return False

    # -- focus model ---------------------------------------------------------
    def _rebuild_focus(self):
        rows = [("option", "arena"), ("option", "size"), ("option", "speed")]
        if self.mode.timed:
            rows.append(("option", "duration"))
        if self.mode.allow_obstacles:
            rows.append(("option", "obstacles"))
        rows += [("roster", i) for i in range(len(self.roster))]
        rows.append(("start", None))
        self.focus_rows = rows
        if self.focus not in rows:
            self.focus = rows[-1]

    def _move_focus(self, delta):
        i = self.focus_rows.index(self.focus)
        self.focus = self.focus_rows[(i + delta) % len(self.focus_rows)]
        self.app.audio.play("menu_move")

    def _adjust(self, delta):
        kind, key = self.focus
        if kind == "start":
            if delta == 0:
                self._start()
            return
        if kind == "roster":
            entry = self.roster[key]
            if entry["device"][0] == "bot":
                i = BOT_DIFFS.index(entry["difficulty"])
                entry["difficulty"] = BOT_DIFFS[(i + delta) % len(BOT_DIFFS)]
            self.app.audio.play("menu_move")
            return
        if key == "arena":
            cur = THEMES.index(self.theme)
            self.theme = THEMES[(cur + delta) % len(THEMES)]
        elif key == "size":
            order = tuple(SIZES)
            self.size = order[(order.index(self.size) + delta) % len(order)]
        elif key == "speed":
            order = tuple(SPEEDS)
            self.speed = order[(order.index(self.speed) + delta) % len(order)]
        elif key == "duration":
            cur = DURATION_OPTIONS.index(self.duration) \
                if self.duration in DURATION_OPTIONS else 1
            self.duration = DURATION_OPTIONS[(cur + delta) % len(DURATION_OPTIONS)]
        elif key == "obstacles":
            self.obstacles = not self.obstacles
        self.app.audio.play("menu_move")

    def _toggle_team(self):
        kind, key = self.focus
        if kind == "roster" and self.mode.teams:
            entry = self.roster[key]
            entry["team"] = 1 - entry["team"]
            self.app.audio.play("menu_move")

    # -- option labels ---------------------------------------------------------
    def _option_label(self, key):
        return {"arena": "Arena", "size": "Arena size", "speed": "Game speed",
                "duration": "Match duration",
                "obstacles": "Obstacles"}[key]

    def _option_value(self, key):
        if key == "arena":
            return {"nokia": "Nokia Classic", "neon": "Neon Grid",
                    "industrial": "Industrial", "circuit": "Circuit",
                    "minimal": "Minimal"}[self.theme]
        if key == "size":
            return self.size.title()
        if key == "speed":
            return self.speed.title()
        if key == "duration":
            return f"{self.duration}s"
        if key == "obstacles":
            return "On" if self.obstacles else "Off"
        return ""

    def _roster_label(self, i):
        entry = self.roster[i]
        device = entry["device"]
        name = f"P{i + 1}"
        if device[0] == "kb":
            desc = "Keyboard WASD" if device[1] == 0 else "Arrow keys"
        elif device[0] == "pad":
            desc = f"Controller {device[1] + 1}"
            pad_name = self.app.input.pad_name(device[1])
            if pad_name:
                desc += f" ({pad_name})"
        else:
            desc = f"Bot - {entry['difficulty'].title()}"
        if self.mode.teams:
            desc += f"   Team {entry['team'] + 1}"
        return f"{name}: {desc}"

    # -- match start ---------------------------------------------------------
    def _start(self):
        from ...core.match import PlayerSlot
        players = []
        visuals = {}
        controllers = {}
        slot_cfg = self.app.settings.get("players")
        for i, entry in enumerate(self.roster):
            device = entry["device"]
            sid = len(players)
            if device[0] == "bot":
                players.append(PlayerSlot(
                    sid, f"P{i+1} Bot", kind="bot",
                    difficulty=entry["difficulty"],
                    team=entry["team"] if self.mode.teams else None))
            else:
                players.append(PlayerSlot(
                    sid, f"P{i+1}", kind="human",
                    team=entry["team"] if self.mode.teams else None))
                self.app.input.bind_player(sid, device)
                controllers[sid] = self.app.input.controller_for(sid)
            vis = slot_cfg[i] if i < len(slot_cfg) else {}
            visuals[sid] = {"color": vis.get("color", i),
                            "pattern": vis.get("pattern", "solid"),
                            "head": vis.get("head", "classic")}
        try:
            self.app.start_match(self.mode.key, players, visuals, controllers,
                                 theme=self.theme, size=self.size,
                                 speed=self.speed, duration=self.duration,
                                 obstacles=self.obstacles)
        except ValueError as exc:
            self.app.toast(str(exc))

    # -- screen protocol -----------------------------------------------------
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            name = pygame.key.name(ev.key)
            if ev.key == pygame.K_ESCAPE:
                self.app.pop_screen()
            elif ev.key in (pygame.K_TAB,):
                self._move_focus(-1 if ev.mod & pygame.KMOD_SHIFT else 1)
            elif ev.key == pygame.K_LEFT:
                self._adjust(-1)
            elif ev.key == pygame.K_RIGHT:
                self._adjust(1)
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.focus[0] == "start":
                    self.app.audio.play("menu_select")
                    self._start()
                else:
                    self._adjust(1)
            elif ev.key == pygame.K_b:
                if not self._add_bot():
                    self.app.toast("No room for more bots")
            elif ev.key == pygame.K_x:
                if not self._remove_bot():
                    self.app.toast("No bot to remove")
            elif ev.key == pygame.K_t:
                self._toggle_team()
            else:
                self._handle_lobby_key(name)
        elif ev.type == pygame.JOYBUTTONDOWN:
            slot = self._pad_slot_for(ev)
            if ev.button in (8, 9):
                self.app.pop_screen()
            elif ev.button == 1:
                if slot is not None:
                    self._leave(("pad", slot))
            elif ev.button == 0:
                if slot is None:
                    return
                device = ("pad", slot)
                if self._joined(device):
                    if self.focus[0] == "start":
                        self._start()
                    else:
                        self._adjust(1)
                else:
                    if not self._join(device):
                        self.app.toast("Lobby is full")
        elif ev.type == pygame.JOYHATMOTION and ev.value != (0, 0):
            if ev.value[1] > 0:
                self._move_focus(-1)
            elif ev.value[1] < 0:
                self._move_focus(1)
            elif ev.value[0] < 0:
                self._adjust(-1)
            elif ev.value[0] > 0:
                self._adjust(1)

    def _pad_slot_for(self, ev):
        instance = getattr(ev, "instance_id", None)
        if instance is None:
            instance = getattr(ev, "joy", None)
        for slot, inst in self.app.input.pad_slots.items():
            if inst is not None and inst == instance:
                return slot
        return None

    # -- drawing ---------------------------------------------------------
    def draw(self, surf):
        surf.fill(BG)
        t = font(56).render(self.mode.title, True, ACCENT)
        surf.blit(t, t.get_rect(center=(LOGICAL_W // 2, 44)))
        d = font(24).render(self.mode.description, True, DIM)
        surf.blit(d, d.get_rect(center=(LOGICAL_W // 2, 80)))

        panel = pygame.Rect(LOGICAL_W // 2 - 430, 104, 860, 556)
        draw_panel(surf, panel)
        y = panel.y + 14
        row_h = 36

        # Option rows
        for kind, key in self.focus_rows:
            if kind != "option":
                continue
            selected = self.focus == (kind, key)
            if selected:
                hl = pygame.Rect(panel.x + 12, y - 4, panel.width - 24,
                                 row_h - 4)
                pygame.draw.rect(surf, (44, 60, 76), hl, border_radius=6)
            name = font(30).render(self._option_label(key), True,
                                   ACCENT if selected else TEXT)
            surf.blit(name, (panel.x + 26, y))
            value = self._option_value(key)
            v = font(28).render(f"< {value} >", True,
                                TEXT if selected else DIM)
            surf.blit(v, (panel.right - 26 - v.get_width(), y))
            y += row_h

        # Roster
        y += 4
        surf.blit(font(26).render("PLAYERS", True, DIM), (panel.x + 26, y))
        y += 28
        for i, entry in enumerate(self.roster):
            selected = self.focus == ("roster", i)
            if selected:
                hl = pygame.Rect(panel.x + 12, y - 4, panel.width - 24,
                                 row_h - 4)
                pygame.draw.rect(surf, (44, 60, 76), hl, border_radius=6)
            chip = pygame.Rect(panel.x + 26, y + 6, 16, 16)
            vis = self.app.settings.get("players")
            color_i = vis[i].get("color", i) if i < len(vis) else i
            pygame.draw.rect(surf, player_color(color_i), chip,
                             border_radius=3)
            label = font(28).render(self._roster_label(i), True,
                                    ACCENT if selected else TEXT)
            surf.blit(label, (panel.x + 52, y))
            if entry["device"][0] == "bot":
                hint = font(22).render("Left/Right: difficulty", True, DIM)
                surf.blit(hint, (panel.right - 26 - hint.get_width(), y + 4))
            elif self.mode.teams:
                hint = font(22).render("T: change team", True, DIM)
                surf.blit(hint, (panel.right - 26 - hint.get_width(), y + 4))
            y += row_h
        if not self.roster:
            surf.blit(font(26).render("Nobody yet - press a key on your "
                                      "device to join", True, DIM),
                      (panel.x + 52, y))
            y += row_h

        # Join hints
        y += 4
        hints = ["W: join WASD   S: leave",
                 "Up: join arrows   Down: leave",
                 "Pad btn 1: join   btn 2: leave",
                 "B: add bot   X: remove bot"]
        for hi, h in enumerate(hints):
            hx = panel.x + 26 + (hi % 2) * 420
            hy = y + (hi // 2) * 22
            surf.blit(font(22).render(h, True, DIM), (hx, hy))
        y += 48

        # START
        selected = self.focus[0] == "start"
        s = font(34).render("START MATCH", True,
                            (20, 20, 26) if selected else ACCENT)
        sr = s.get_rect(center=(panel.centerx, y + 16))
        if selected:
            pygame.draw.rect(surf, ACCENT, sr.inflate(44, 14),
                             border_radius=8)
        surf.blit(s, sr)

        foot = font(24).render(
            "Tab: navigate   Left/Right: change   Enter: start   Esc: back",
            True, DIM)
        surf.blit(foot, foot.get_rect(center=(LOGICAL_W // 2, LOGICAL_H - 22)))
