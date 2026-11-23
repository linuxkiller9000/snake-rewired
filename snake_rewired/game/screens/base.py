"""UI framework: screens, menus, toasts. Logical surface is 1366x768."""

import pygame

from ..render import LOGICAL_W, LOGICAL_H

FONT_CACHE = {}


def font(size):
    f = FONT_CACHE.get(size)
    if f is None:
        f = pygame.font.Font(None, size)
        FONT_CACHE[size] = f
    return f


ACCENT = (90, 220, 255)
TEXT = (228, 228, 234)
DIM = (140, 140, 150)
BG = (12, 12, 18)
PANEL = (22, 22, 30)
PANEL_LINE = (58, 58, 72)


class Screen:
    def on_enter(self, **kwargs):
        pass

    def handle_event(self, ev):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


class Toast:
    def __init__(self, text, seconds=2.4):
        self.text = text
        self.remaining = seconds

    def draw(self, surf):
        f = font(26)
        label = f.render(self.text, True, (20, 20, 26))
        r = label.get_rect(center=(LOGICAL_W // 2, LOGICAL_H - 44))
        bg = r.inflate(28, 14)
        pygame.draw.rect(surf, (250, 230, 140), bg, border_radius=8)
        surf.blit(label, r)


class MenuScreen(Screen):
    """Vertical keyboard/gamepad navigable menu."""

    title = ""
    subtitle = ""

    def __init__(self, app):
        self.app = app
        self.items = []          # (label, callback) or (label, None)
        self.index = 0
        self.footer = "Up/Down: navigate   Enter: select   Esc: back"
        self._build()

    def _build(self):
        pass

    def add(self, label, callback=None):
        self.items.append([label, callback])

    def on_enter(self, **kwargs):
        self.index = min(self.index, max(0, len(self.items) - 1))

    def _move(self, delta):
        if not self.items:
            return
        self.index = (self.index + delta) % len(self.items)
        self.app.audio.play("menu_move")

    def _activate(self):
        if not self.items:
            return
        cb = self.items[self.index][1]
        if cb is not None:
            self.app.audio.play("menu_select")
            cb()

    def back(self):
        self.app.pop_screen()

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_UP, pygame.K_w):
                self._move(-1)
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self._move(1)
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate()
            elif ev.key == pygame.K_ESCAPE:
                self.app.audio.play("pause")
                self.back()
        elif ev.type == pygame.JOYHATMOTION and ev.value != (0, 0):
            if ev.value[1] > 0:
                self._move(-1)
            elif ev.value[1] < 0:
                self._move(1)
        elif ev.type == pygame.JOYBUTTONDOWN and ev.button in (0, 1):
            self._activate()
        elif ev.type == pygame.JOYBUTTONDOWN and ev.button in (8, 9):
            self.back()

    def update(self, dt):
        pass

    def draw_title_block(self, surf, y=64):
        t = font(72).render(self.title, True, ACCENT)
        surf.blit(t, t.get_rect(center=(LOGICAL_W // 2, y)))
        if self.subtitle:
            s = font(28).render(self.subtitle, True, DIM)
            surf.blit(s, s.get_rect(center=(LOGICAL_W // 2, y + 44)))

    def draw(self, surf):
        surf.fill(BG)
        self.draw_title_block(surf)
        y0 = 200 if self.subtitle else 160
        for i, (label, cb) in enumerate(self.items):
            selected = i == self.index
            f = font(40 if selected else 34)
            color = (20, 20, 26) if selected else (TEXT if cb else DIM)
            label_s = f.render(label, True, color)
            r = label_s.get_rect(center=(LOGICAL_W // 2, y0 + i * 52))
            if selected:
                bg = r.inflate(44, 12)
                pygame.draw.rect(surf, ACCENT, bg, border_radius=10)
            surf.blit(label_s, r)
        f = font(24)
        foot = f.render(self.footer, True, DIM)
        surf.blit(foot, foot.get_rect(center=(LOGICAL_W // 2, LOGICAL_H - 24)))


def draw_panel(surf, rect, line=PANEL_LINE):
    pygame.draw.rect(surf, PANEL, rect, border_radius=10)
    pygame.draw.rect(surf, line, rect, 1, border_radius=10)


def wrap_text(text, f, width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if f.size(trial)[0] <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
