"""World renderer: interpolated snake movement, food, HUD.

Renders into a logical 1366x768 surface; the app scales it to the window.
Snake positions interpolate between the previous and current grid step so
movement is smooth at any frame rate while the simulation stays discrete.
"""

import math

import pygame

from .themes import (FOOD_COLORS, PLAYER_COLORS, HIGH_CONTRAST_COLORS,
                     get_theme)

LOGICAL_W, LOGICAL_H = 1366, 768
ARENA_MARGIN = 18


def player_color(index, high_contrast=False):
    palette = HIGH_CONTRAST_COLORS if high_contrast else PLAYER_COLORS
    return palette[index % len(palette)][1]


def player_color_name(index):
    return PLAYER_COLORS[index % len(PLAYER_COLORS)][0]


class Layout:
    """Arena fills the whole window; the HUD floats over it (compact,
    translucent, top-left) so the playfield gets maximum space."""

    def __init__(self, arena):
        avail_w = LOGICAL_W - ARENA_MARGIN * 2
        avail_h = LOGICAL_H - ARENA_MARGIN * 2
        self.cell = max(6, min(avail_w // arena.cols, avail_h // arena.rows))
        w = self.cell * arena.cols
        h = self.cell * arena.rows
        self.rect = pygame.Rect(ARENA_MARGIN + (avail_w - w) // 2,
                                ARENA_MARGIN + (avail_h - h) // 2, w, h)

    def cell_rect(self, pos):
        return pygame.Rect(self.rect.x + pos[0] * self.cell,
                           self.rect.y + pos[1] * self.cell,
                           self.cell, self.cell)

    def cell_center(self, pos):
        r = self.cell_rect(pos)
        return r.center


class SnakeSkin:
    """Visual identity of one snake: color, pattern, head style."""

    def __init__(self, color_index, pattern="solid", head="classic",
                 high_contrast=False):
        self.color = player_color(color_index, high_contrast)
        self.pattern = pattern
        self.head = head

    def darker(self, factor=0.62):
        return tuple(int(c * factor) for c in self.color)


def draw_snake(surf, layout, cells_px, skin, number, alive=True,
               alpha=255, blink=False):
    """cells_px: interpolated pixel centers, head first."""
    if blink and (pygame.time.get_ticks() // 160) % 2 == 0:
        return
    cell = layout.cell
    body = skin.color
    dark = skin.darker()
    width = max(3, cell - 2)
    if alpha < 255:
        body = (*body, alpha)
        dark = (*dark, alpha)
    # Body: connected thick polyline through centers, tail to head.
    if len(cells_px) >= 2:
        pygame.draw.lines(surf, body, False, list(reversed(cells_px)), width)
    for i, (x, y) in enumerate(cells_px):
        r = pygame.Rect(0, 0, width, width)
        r.center = (int(x), int(y))
        if i == 0:
            continue  # head drawn last
        if skin.pattern == "striped" and i % 2 == 0:
            pygame.draw.rect(surf, dark, r, border_radius=max(2, cell // 5))
        elif skin.pattern == "dotted":
            pygame.draw.rect(surf, body, r, border_radius=max(2, cell // 5))
            pygame.draw.circle(surf, dark, r.center, max(1, cell // 6))
        elif skin.pattern == "scaled":
            pygame.draw.rect(surf, body, r, border_radius=2)
            pygame.draw.rect(surf, dark, r, 1, border_radius=2)
        elif skin.pattern == "circuit":
            pygame.draw.rect(surf, body, r, border_radius=2)
            pygame.draw.circle(surf, dark, r.center, max(1, cell // 8))
        elif skin.pattern == "golden":
            grad = pygame.Rect(r)
            pygame.draw.rect(surf, body, grad, border_radius=max(2, cell // 5))
            pygame.draw.rect(surf, (255, 240, 180), r.inflate(-cell // 3, -cell // 3),
                             border_radius=2)
        else:
            pygame.draw.rect(surf, body, r, border_radius=max(2, cell // 5))
    # Head
    hx, hy = cells_px[0]
    hr = pygame.Rect(0, 0, width + 2, width + 2)
    hr.center = (int(hx), int(hy))
    if skin.head == "visor":
        pygame.draw.rect(surf, dark, hr, border_radius=max(2, cell // 4))
        band = hr.copy()
        band.height = max(2, cell // 4)
        band.centery = hr.centery
        pygame.draw.rect(surf, (230, 240, 255), band, border_radius=2)
    elif skin.head == "arrow":
        pygame.draw.polygon(surf, body,
                            [hr.midtop, hr.midright, hr.midbottom, hr.midleft])
        pygame.draw.polygon(surf, dark,
                            [hr.midtop, hr.midright, hr.midbottom, hr.midleft], 2)
    else:  # classic: rounded square with eyes toward direction handled by app
        pygame.draw.rect(surf, dark if alive else (120, 120, 120), hr,
                         border_radius=max(2, cell // 4))
        pygame.draw.rect(surf, body, hr.inflate(-3, -3),
                         border_radius=max(2, cell // 4))
    # Player number badge (distinguishability beyond color).
    if number is not None and cell >= 10:
        font = getattr(draw_snake, "_font", None)
        if font is None or font.get_height() != max(10, cell - 2):
            font = pygame.font.Font(None, max(10, cell - 2))
            draw_snake._font = font
        badge = font.render(str(number), True, (15, 15, 20))
        br = badge.get_rect(center=(int(hx), int(hy)))
        bg = pygame.Rect(0, 0, br.width + 4, br.height + 2)
        bg.center = br.center
        pygame.draw.rect(surf, (245, 245, 245), bg, border_radius=3)
        surf.blit(badge, br)


def draw_food(surf, layout, item, tick, palette=None):
    r = layout.cell_rect(item.pos)
    color = (palette or FOOD_COLORS)[item.kind]
    cx, cy = r.center
    pulse = 1.0 + 0.12 * math.sin(tick * 0.3 + item.pos[0])
    if item.expiring_soon and (tick // 3) % 2 == 0:
        return  # blink before expiring
    rad = max(2, int(layout.cell * 0.34 * pulse))
    if item.kind == "normal":
        pygame.draw.circle(surf, color, (cx, cy), rad)
        pygame.draw.circle(surf, (255, 200, 200), (cx - rad // 3, cy - rad // 3),
                           max(1, rad // 3))
    elif item.kind == "bonus":
        pygame.draw.polygon(surf, color, [(cx, cy - rad), (cx + rad, cy),
                                          (cx, cy + rad), (cx - rad, cy)])
    elif item.kind == "golden":
        pygame.draw.circle(surf, color, (cx, cy), rad + 2, 2)
        pygame.draw.polygon(surf, color, [(cx, cy - rad), (cx + rad, cy),
                                          (cx, cy + rad), (cx - rad, cy)])
    elif item.kind == "speed":
        pygame.draw.polygon(surf, color, [(cx - rad, cy - rad // 2),
                                          (cx, cy - rad // 2),
                                          (cx - rad // 3, cy + rad),
                                          (cx + rad // 3, cy),
                                          (cx - rad // 2, cy),
                                          (cx + rad // 2, cy - rad)])
    elif item.kind == "slow":
        pygame.draw.circle(surf, color, (cx, cy), rad, 2)
        pygame.draw.line(surf, color, (cx, cy), (cx, cy - rad + 2), 2)
        pygame.draw.line(surf, color, (cx, cy), (cx + rad - 3, cy), 2)


class WorldRenderer:
    """Draws one match frame into the logical surface."""

    def __init__(self, match, players_visual, settings):
        self.match = match
        self.theme = get_theme(match.arena.theme)
        self.layout = Layout(match.arena)
        self.settings = settings
        hc = bool(settings.get("high_contrast"))
        self.skins = {}
        for sid, vis in players_visual.items():
            self.skins[sid] = SnakeSkin(vis["color"], vis["pattern"],
                                        vis["head"], hc)
        # Nokia monochrome mode: a lone snake on the Nokia arena renders in
        # authentic LCD dark-green. Multiplayer keeps distinct colors.
        self.food_palette = None
        if match.arena.theme == "nokia":
            lcd = {k: (67, 82, 61) for k in FOOD_COLORS}
            if len(self.skins) == 1:
                only = next(iter(self.skins.values()))
                only.color = (67, 82, 61)
                self.food_palette = lcd
        self._bg_cache = None
        self._font = None
        self._font_big = None

    @property
    def font(self):
        if self._font is None:
            self._font = pygame.font.Font(None, 26)
        return self._font

    @property
    def font_big(self):
        if self._font_big is None:
            self._font_big = pygame.font.Font(None, 44)
        return self._font_big

    def draw(self, surf, alpha=None, elimination_flash=None):
        m = self.match
        if alpha is None:
            alpha = m.interpolation_alpha()
        # Arena background (cached: it never changes mid-match).
        if self._bg_cache is None:
            bg = pygame.Surface(self.layout.rect.size)
            self.theme.draw_background(bg, bg.get_rect(),
                                       bool(self.settings.get("show_grid")),
                                       self.layout.cell)
            for pos in m.arena.obstacles:
                r = pygame.Rect(pos[0] * self.layout.cell,
                                pos[1] * self.layout.cell,
                                self.layout.cell, self.layout.cell)
                self.theme.draw_obstacle(bg, r)
            self._bg_cache = bg
        surf.fill((12, 12, 16))
        surf.blit(self._bg_cache, self.layout.rect)
        self.theme.draw_border(surf, self.layout.rect)

        for item in m.food.items.values():
            draw_food(surf, self.layout, item, m.tick, self.food_palette)

        # Snakes, interpolated between previous and current grid cells.
        for sid, snake in m.snakes.items():
            skin = self.skins[sid]
            cells = list(snake.cells)
            if not snake.alive:
                self._draw_ghost(surf, cells, skin, sid)
                continue
            px = self._interpolated_centers(snake, cells, alpha)
            number = None if len(self.skins) == 1 else sid + 1
            draw_snake(surf, self.layout, px, skin, number)
            # Eyes showing direction
            d = snake.direction
            hx, hy = px[0]
            ex = int(hx + d[0] * self.layout.cell * 0.18)
            ey = int(hy + d[1] * self.layout.cell * 0.18)
            off = max(2, self.layout.cell // 6)
            perp = (-d[1], d[0])
            for sgn in (-1, 1):
                pygame.draw.circle(
                    surf, (20, 20, 25),
                    (ex + perp[0] * off * sgn, ey + perp[1] * off * sgn),
                    max(1, self.layout.cell // 8))

        self._draw_hud(surf)

    def _interpolated_centers(self, snake, cells, alpha):
        """Pixel centers lerped between the previous and current step.

        Segment mapping: head lerps from the old head toward the new head;
        body segment i follows where segment i-1 was. With growth, the new
        tail segment sits on the old tail."""
        prev = self.match.prev_cells.get(snake.sid)
        if not prev or alpha >= 1.0 or len(cells) < 2:
            return [self.layout.cell_center(c) for c in cells]
        out = []
        for i, c in enumerate(cells):
            if i == 0:
                p = prev[0]
            elif i - 1 < len(prev):
                p = prev[i - 1]
            else:
                p = prev[-1]
            cx, cy = self.layout.cell_center(c)
            px, py = self.layout.cell_center(p)
            out.append((px + (cx - px) * alpha, py + (cy - py) * alpha))
        return out

    def _draw_ghost(self, surf, cells, skin, sid):
        # Eliminated snakes fade as a translucent outline.
        if not cells:
            return
        px = [self.layout.cell_center(c) for c in cells[:24]]
        ghost = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        width = max(3, self.layout.cell - 2)
        if len(px) >= 2:
            pygame.draw.lines(ghost, (*skin.color, 45), False,
                              list(reversed(px)), width)
        surf.blit(ghost, (0, 0))

    def _draw_hud(self, surf):
        """Compact floating status panel, top-left, translucent so the
        arena stays visible underneath."""
        m = self.match
        small = pygame.font.Font(None, 22)
        lines = []
        header = m.mode.title
        if m.time_remaining is not None:
            secs = int(m.time_remaining)
            header += f"   {secs // 60}:{secs % 60:02d}"
        lines.append((header, (235, 235, 240), None))
        for sid in sorted(m.snakes):
            snake = m.snakes[sid]
            skin = self.skins[sid]
            name = snake.name
            if snake.team is not None:
                name += f" T{snake.team + 1}"
            if snake.alive:
                info = f"{snake.score}  len {snake.length}"
                if snake.speed_effect:
                    info += f"  {snake.speed_effect[:3].upper()}"
                text = f"{name}  {info}"
                color = (225, 225, 230)
            else:
                text = f"{name}  OUT {snake.score}"
                color = (150, 148, 155)
            lines.append((text, color, skin.color))
        if m.mode.teams:
            scores = {}
            for s in m.snakes.values():
                scores[s.team] = scores.get(s.team, 0) + s.score
            tline = "   ".join(f"T{t + 1} {scores[t]}" for t in sorted(scores))
            lines.append((tline, (240, 220, 140), None))
        rendered = [(small.render(t, True, c), chip) for t, c, chip in lines]
        chip_w = 18
        width = max(r.get_width() + (chip_w if chip else 0)
                    for r, chip in rendered) + 20
        height = len(rendered) * 20 + 12
        x = self.layout.rect.x + 10
        y = self.layout.rect.y + 10
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((14, 14, 20, 120))
        pygame.draw.rect(panel, (90, 90, 105, 140), panel.get_rect(), 1,
                         border_radius=6)
        ry = 6
        for r, chip in rendered:
            tx = 10
            if chip is not None:
                pygame.draw.rect(panel, chip,
                                 (10, ry + 4, 12, 12), border_radius=3)
                tx += chip_w
            panel.blit(r, (tx, ry))
            ry += 20
        surf.blit(panel, (x, y))
        self.hud_rect = pygame.Rect(x, y, width, height)
