# SNAKE: REWIRED

A complete, lightweight 2D Snake arcade game for Linux and Windows.
Classic Nokia-style gameplay expanded into a local multiplayer game for up
to **six simultaneous players on one shared arena**.

- Python 3 + pygame-ce. No internet, accounts, or native extensions.
- Fixed-grid simulation separated from rendering: game speed never depends
  on frame rate.
- Designed for low-end machines and 1366x768 displays.

## Quick start

### Linux

    sh run.sh

`run.sh` automatically creates a private Python environment (`.venv`) and
installs pygame-ce on first run - no manual setup. **The first run needs
internet once** to download pygame-ce; after that the game is fully
offline forever. You need `python3` and `python3-venv` (on Arch:
`sudo pacman -S python`; on Debian/Ubuntu: `sudo apt install python3-venv`).
Prefer zero setup? Use the standalone Linux build instead - one file,
no Python to install, no internet needed at all. It bundles Python 3.10,
pygame-ce and SDL2; verified on glibc Linux (Ubuntu 22.04 container)
with X11 or Wayland/XWayland. It still relies on normal system graphics
and sound libraries.

### Windows

Double-click `run.bat` (needs Python 3.10+ from python.org installed; the
launcher sets up everything else).

## Controls

| Player | Device | Keys |
|--------|--------|------|
| P1 | Keyboard | W A S D |
| P2 | Keyboard | Arrow keys |
| P3-P6 | Controllers 1-4 | D-pad (stick and face buttons optional) |

Menus: Up/Down + Enter, Esc back. Controllers navigate menus with the
D-pad and the first face button. Pause: Esc or P (Start on a controller).
Rematch from results: R.

Keyboard remapping lives in Settings. See CONTROLS.md for details.

## Game modes

- **Classic** - faithful Nokia Snake: normal food, rising speed,
  high-score chase, no power-ups. Play alone, or press B in setup to add
  bots (or let a second keyboard player join with the arrow keys).
- **Battle Arena** - 2-6 players, last snake alive wins.
- **Score Race** - highest score when the clock runs out.
- **Team Survival** - two teams; teammates still collide with each other.

## Collision rules (classic, identical for humans and AI)

Moving into a wall, obstacle, your own body or another snake's body kills
you. Two heads entering the same cell kill both. Two snakes swapping head
cells kill both. A cell at another snake's tail is safe if that snake is
moving away and not growing. All deaths in a tick are resolved
simultaneously - no ordering advantage. Full write-up in
`snake_rewired/core/rules.py`.

## Arenas

Five themes (Nokia Classic, Neon Grid, Industrial, Circuit, Minimal), each
in small / medium / large, with optional symmetric obstacle patterns in
arcade modes. Classic stays a faithful empty box.

## Testing

    python3 -m unittest discover -s tests -t . -v

Headless six-player runtime test with screenshots:

    python3 tools/scripted_run.py /tmp/snake_shots

## Project layout

    main.py                 entry point
    snake_rewired/core/     grid simulation (no pygame): snakes, rules,
                            arenas, food, modes, match orchestration
    snake_rewired/ai/       Easy/Normal/Hard bot brains
    snake_rewired/game/     settings, save system, input, audio, rendering
    snake_rewired/game/screens/  menus, setup, gameplay, results
    tests/                  automated unit tests
    tools/scripted_run.py   end-to-end synthetic-input runtime test

## Honest platform status

- Linux: verified headless (SDL dummy) with the full menu-to-results flow
  and all 37 unit tests passing. X11/Wayland desktop behavior uses standard
  pygame display code paths.
- Windows: same code, but **not runtime-tested on Windows** - the launcher
  and code use portable paths only.
- Controllers: the six-player input pipeline is tested with synthetic
  virtual gamepads (D-pad, buttons, stick). Physical controller hardware
  has **not** been tested by the developer; D-pad works with standard SDL
  gamepad mappings.
- 60 FPS: the game renders only on change-heavy frames and draws simple
  primitives; no per-target-machine benchmark is claimed yet.
