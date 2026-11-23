"""Arena visual themes: five distinct identities, not recolors.

Each theme owns: background base + pattern draw, grid style, border style,
obstacle rendering, food styling and snake palette accents. All drawing is
cheap pygame primitives - no GPU effects.
"""

import pygame

# Six player colors, chosen to stay distinguishable side by side and to
# survive the high-contrast palette swap.
PLAYER_COLORS = [
    ("Lime",   (80, 220, 60)),
    ("Pink",   (240, 80, 170)),
    ("Cyan",   (60, 200, 230)),
    ("Orange", (245, 150, 40)),
    ("Violet", (160, 110, 245)),
    ("Yellow", (235, 220, 60)),
]
HIGH_CONTRAST_COLORS = [
    ("White",  (255, 255, 255)),
    ("Red",    (255, 60, 60)),
    ("Cyan",   (0, 255, 255)),
    ("Yellow", (255, 255, 0)),
    ("Magenta", (255, 0, 255)),
    ("Green",  (0, 255, 0)),
]

FOOD_COLORS = {
    "normal": (235, 70, 70),
    "bonus": (250, 190, 60),
    "golden": (255, 225, 90),
    "speed": (90, 200, 255),
    "slow": (170, 120, 255),
}


def _checker(surface, rect, c1, c2, n=8):
    w = rect.width // n
    for i in range(n):
        for j in range(n):
            color = c1 if (i + j) % 2 == 0 else c2
            pygame.draw.rect(surface, color,
                             (rect.x + i * w, rect.y + j * w, w, w))


class Theme:
    key = "base"
    title = "Base"
    bg = (20, 20, 26)
    grid_line = None           # None = no lines
    border = (90, 90, 100)
    obstacle = (70, 70, 80)
    obstacle_detail = None
    floor_detail = None

    def draw_background(self, surf, rect, show_grid, cell):
        surf.fill(self.bg, rect)
        self.draw_floor(surf, rect, cell)
        if show_grid and self.grid_line is not None and cell >= 8:
            for x in range(rect.x, rect.right, cell):
                pygame.draw.line(surf, self.grid_line, (x, rect.y),
                                 (x, rect.bottom))
            for y in range(rect.y, rect.bottom, cell):
                pygame.draw.line(surf, self.grid_line, (rect.x, y),
                                 (rect.right, y))

    def draw_floor(self, surf, rect, cell):
        pass

    def draw_border(self, surf, rect):
        pygame.draw.rect(surf, self.border, rect, 3)

    def draw_obstacle(self, surf, rect):
        pygame.draw.rect(surf, self.obstacle, rect)
        pygame.draw.rect(surf, self.obstacle_detail or self.border, rect, 2)


class NokiaTheme(Theme):
    key = "nokia"
    title = "Nokia Classic"
    bg = (155, 178, 122)          # classic LCD green
    grid_line = (147, 168, 116)
    border = (67, 82, 61)
    obstacle = (67, 82, 61)
    obstacle_detail = (56, 68, 51)

    def draw_floor(self, surf, rect, cell):
        # LCD pixel-dotted floor
        step = max(6, cell // 2)
        dot = (149, 171, 118)
        for y in range(rect.y + step // 2, rect.bottom, step):
            for x in range(rect.x + step // 2, rect.right, step):
                surf.set_at((x, y), dot)

    def draw_border(self, surf, rect):
        pygame.draw.rect(surf, self.border, rect, 4)
        pygame.draw.rect(surf, self.obstacle_detail, rect, 1)


class NeonTheme(Theme):
    key = "neon"
    title = "Neon Grid"
    bg = (8, 10, 26)
    grid_line = (24, 30, 64)
    border = (60, 220, 255)
    obstacle = (30, 20, 70)
    obstacle_detail = (150, 60, 255)

    def draw_floor(self, surf, rect, cell):
        # Perspective glow strips at the edges
        glow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for i, alpha in enumerate(range(26, 0, -4)):
            pygame.draw.rect(glow, (40, 60, 160, alpha),
                             glow.get_rect().inflate(-i * 40, -i * 28), 2)
        surf.blit(glow, rect)

    def draw_border(self, surf, rect):
        for i, c in enumerate(((20, 60, 90), (40, 140, 200), (60, 220, 255))):
            pygame.draw.rect(surf, c, rect.inflate(-i * 2, -i * 2), 1)
        pygame.draw.rect(surf, (120, 245, 255), rect, 1)

    def draw_obstacle(self, surf, rect):
        pygame.draw.rect(surf, self.obstacle, rect, border_radius=3)
        pygame.draw.rect(surf, self.obstacle_detail, rect, 2, border_radius=3)


class IndustrialTheme(Theme):
    key = "industrial"
    title = "Industrial"
    bg = (38, 38, 42)
    grid_line = (48, 48, 54)
    border = (190, 160, 60)
    obstacle = (72, 72, 78)
    obstacle_detail = (150, 150, 160)

    def draw_floor(self, surf, rect, cell):
        # Diamond-plate metal: staggered rivet dots
        step = max(10, cell)
        riv = (56, 56, 62)
        for j, y in enumerate(range(rect.y + step // 2, rect.bottom, step)):
            off = step // 2 if j % 2 else 0
            for x in range(rect.x + off + step // 2, rect.right, step):
                pygame.draw.circle(surf, riv, (x, y), 2)

    def draw_border(self, surf, rect):
        pygame.draw.rect(surf, (70, 70, 76), rect, 6)
        # Hazard stripes on the frame
        stripe = 12
        for x in range(rect.x, rect.right, stripe * 2):
            pygame.draw.polygon(surf, self.border,
                                [(x, rect.y - 3), (x + stripe, rect.y - 3),
                                 (x, rect.y + 3)])
            pygame.draw.polygon(surf, self.border,
                                [(x, rect.bottom + 3), (x + stripe, rect.bottom + 3),
                                 (x, rect.bottom - 3)])

    def draw_obstacle(self, surf, rect):
        pygame.draw.rect(surf, self.obstacle, rect)
        pygame.draw.rect(surf, self.obstacle_detail, rect, 2)
        r = rect.inflate(-6, -6)
        for cx, cy in ((r.x, r.y), (r.right, r.y), (r.x, r.bottom),
                       (r.right, r.bottom)):
            pygame.draw.circle(surf, (30, 30, 34), (cx, cy), 2)


class CircuitTheme(Theme):
    key = "circuit"
    title = "Circuit"
    bg = (6, 26, 24)
    grid_line = (12, 44, 40)
    border = (0, 220, 160)
    obstacle = (10, 60, 52)
    obstacle_detail = (240, 200, 80)

    def draw_floor(self, surf, rect, cell):
        # PCB traces: horizontal runs with via dots, deterministic layout
        trace = (16, 70, 60)
        via = (22, 100, 86)
        step = max(12, cell * 2)
        for j, y in enumerate(range(rect.y + step // 2, rect.bottom, step)):
            x0 = rect.x + (j % 3) * 14
            pygame.draw.line(surf, trace, (x0, y), (rect.right - 8, y))
            for x in range(x0 + 24, rect.right - 8, 46):
                pygame.draw.circle(surf, via, (x, y), 2)

    def draw_obstacle(self, surf, rect):
        pygame.draw.rect(surf, self.obstacle, rect, border_radius=2)
        pygame.draw.rect(surf, self.obstacle_detail, rect, 1, border_radius=2)
        pygame.draw.circle(surf, self.obstacle_detail, rect.center, 2)


class MinimalTheme(Theme):
    key = "minimal"
    title = "Minimal"
    bg = (244, 242, 238)
    grid_line = (228, 225, 220)
    border = (60, 60, 70)
    obstacle = (210, 205, 200)
    obstacle_detail = (120, 116, 110)

    def draw_border(self, surf, rect):
        pygame.draw.rect(surf, self.border, rect, 2)

    def draw_obstacle(self, surf, rect):
        pygame.draw.rect(surf, self.obstacle, rect, border_radius=4)
        pygame.draw.rect(surf, self.obstacle_detail, rect, 2, border_radius=4)


THEME_CLASSES = {t.key: t for t in (NokiaTheme, NeonTheme, IndustrialTheme,
                                    CircuitTheme, MinimalTheme)}


def get_theme(key):
    return THEME_CLASSES.get(key, NeonTheme)()
