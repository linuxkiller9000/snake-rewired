"""Grid geometry primitives. Pure Python, no pygame."""

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

DIRECTIONS = (UP, DOWN, LEFT, RIGHT)
DIR_NAMES = {UP: "up", DOWN: "down", LEFT: "left", RIGHT: "right"}
NAME_DIRS = {v: k for k, v in DIR_NAMES.items()}


def add(pos, direction):
    return (pos[0] + direction[0], pos[1] + direction[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def opposite(a, b):
    return a[0] == -b[0] and a[1] == -b[1]


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors4(pos):
    return [add(pos, d) for d in DIRECTIONS]
