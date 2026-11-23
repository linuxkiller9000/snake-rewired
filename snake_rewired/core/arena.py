"""Arena definition: grid size, boundaries, obstacles, spawn points.

Pure Python, no pygame. Visual themes live in game/themes.py; this module
only owns the logical layout each theme requests.
"""

from .geometry import add

SIZES = {
    "small": (30, 20),
    "medium": (40, 26),
    "large": (50, 34),
}

THEMES = ("nokia", "neon", "industrial", "circuit", "minimal")

# Default obstacle pattern per theme (used when obstacles are enabled).
THEME_OBSTACLES = {
    "nokia": "none",        # classic Nokia: empty box
    "neon": "walls",
    "industrial": "pillars",
    "circuit": "cross",
    "minimal": "dots",
}

OBSTACLE_PATTERNS = ("none", "pillars", "walls", "cross", "dots")


def _pattern_cells(pattern, cols, rows):
    """Symmetric obstacle layouts. All patterns keep spawn corridors and a
    margin around edges clear."""
    cells = set()
    cx, cy = cols // 2, rows // 2
    if pattern == "none":
        return cells
    if pattern == "pillars":
        # Four 2x2 blocks at mirrored interior points.
        for ox, oy in ((0.28, 0.30), (0.72, 0.30), (0.28, 0.70), (0.72, 0.70)):
            bx, by = int(cols * ox), int(rows * oy)
            for dx in (0, 1):
                for dy in (0, 1):
                    cells.add((bx + dx, by + dy))
    elif pattern == "walls":
        # Two short horizontal walls, mirrored.
        w = max(4, cols // 8)
        for i in range(w):
            cells.add((cx - w // 2 + i, int(rows * 0.30)))
            cells.add((cx - w // 2 + i, int(rows * 0.70)))
    elif pattern == "cross":
        # Central plus shape with a gap in each arm.
        arm = max(3, min(cols, rows) // 6)
        for i in range(2, arm + 2):
            cells.add((cx - i, cy))
            cells.add((cx + i, cy))
            cells.add((cx, cy - i))
            cells.add((cx, cy + i))
    elif pattern == "dots":
        # Sparse single pillars on a mirrored lattice.
        for fx in (0.30, 0.50, 0.70):
            for fy in (0.30, 0.50, 0.70):
                cells.add((int(cols * fx), int(rows * fy)))
    return {c for c in cells if 0 <= c[0] < cols and 0 <= c[1] < rows}


# Six canonical spawn slots as (x-fraction, y-fraction, direction). Edge
# slots face inward; center-top/bottom slots split left/right traffic.
_SPAWN_SLOTS = (
    (0.06, 0.25, (1, 0)),
    (0.94, 0.25, (-1, 0)),
    (0.06, 0.75, (1, 0)),
    (0.94, 0.75, (-1, 0)),
    (0.35, 0.08, (0, 1)),
    (0.65, 0.92, (0, -1)),
)

SPAWN_LENGTH = 3


class Arena:
    def __init__(self, theme="nokia", size="medium", obstacles=None):
        if theme not in THEMES:
            raise ValueError(f"unknown theme {theme!r}")
        if size not in SIZES:
            raise ValueError(f"unknown size {size!r}")
        self.theme = theme
        self.size = size
        self.cols, self.rows = SIZES[size]
        pattern = THEME_OBSTACLES[theme] if obstacles is None else obstacles
        if pattern not in OBSTACLE_PATTERNS:
            raise ValueError(f"unknown obstacle pattern {pattern!r}")
        self.obstacle_pattern = pattern
        self.obstacles = _pattern_cells(pattern, self.cols, self.rows)
        # Spawn zones must stay clear regardless of pattern.
        for pos, _dir in (self._slot(i) for i in range(6)):
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    self.obstacles.discard((pos[0] + dx, pos[1] + dy))
            self.obstacles.discard(pos)

    def _slot(self, index):
        fx, fy, d = _SPAWN_SLOTS[index]
        x = min(max(int(self.cols * fx), SPAWN_LENGTH), self.cols - SPAWN_LENGTH - 1)
        y = min(max(int(self.rows * fy), SPAWN_LENGTH), self.rows - SPAWN_LENGTH - 1)
        while (x, y) in self.obstacles:
            x = (x + 1) % self.cols
        return (x, y), d

    def spawn_points(self, count):
        """Fair starting positions: (head cell, direction, initial cells)."""
        if not 1 <= count <= 6:
            raise ValueError("spawn_points supports 1..6 snakes")
        if count == 1:
            # Classic solo starts centered, facing right, like the Nokia game.
            head = (self.cols // 4, self.rows // 2)
            return [(head, (1, 0), [(head[0] - i, head[1]) for i in range(SPAWN_LENGTH)])]
        out = []
        for i in range(count):
            pos, d = self._slot(i)
            cells = [(pos[0] - d[0] * k, pos[1] - d[1] * k) for k in range(SPAWN_LENGTH)]
            out.append((pos, d, cells))
        return out

    def in_bounds(self, pos):
        return 0 <= pos[0] < self.cols and 0 <= pos[1] < self.rows

    def is_blocked(self, pos):
        return not self.in_bounds(pos) or pos in self.obstacles

    def free_cells(self, occupied):
        for x in range(self.cols):
            for y in range(self.rows):
                if (x, y) not in self.obstacles and (x, y) not in occupied:
                    yield (x, y)
