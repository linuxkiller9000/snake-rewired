# Test report — SNAKE: REWIRED v0.2.0

## Automated suite
- `python3 -m unittest discover -s tests -t .` — 72 tests, all passing.
- Areas: core snake/arena/food/geometry, collision & elimination rules
  (head-on, wall, body, simultaneous same-tick resolution, tie-breaks),
  speed-effect unequal-tick collisions, AI fairness (Easy/Normal/Hard),
  mode end/tie rules (classic, score race, survival, team battle, battle
  royale), persistence (save/load, corruption recovery), unlocks,
  input mapping & reversal/queue fairness, controller button remapping.

## Scripted end-to-end runs (SDL dummy driver)
- `tools/scripted_run.py` — 6-player pipeline: menu -> setup -> match ->
  pause -> results -> rematch; screenshots inspected.
- `tools/theme_gallery.py` — all 5 arena themes rendered and inspected.
- `tools/mode_verification.py` — score race, team survival, pause menu.

## Display
- Logical 1366x768 canvas, RESIZABLE | SCALED window. Verified under X11
  (Xvfb): window created at 1366x768, resized to 1024x600 and 1600x900
  with correct logical scaling; fullscreen toggle + restore exercised.
- VSync: requested when available; app falls back to plain set_mode if the
  driver rejects vsync. Accepted by both the dummy driver and X11 here.

## Performance (measured, 1-core container, Python 3.10)
- Render: ~2.1 ms/frame worst case (6 players, large arena).
- Simulation: ~8 ms/tick worst case (6 hard bots, large arena).
- These are container numbers only; no claims extrapolated to other hardware.

## Platform status
- Linux: built and boot-verified (source ZIP from fresh extraction;
  standalone boots headless; all shared libs resolve).
- Windows: run.bat/bootstrap included, code path written, NOT tested on a
  real Windows machine.
- Physical gamepads: input/remap/poll code tested with synthetic joystick
  events only; no physical pad was available. Identical pads share USB
  GUIDs, so slot assignment is detection order — pick slots manually in
  setup if needed (see CONTROLS.md).

## Runtime requirements
- Source ZIP: Python 3.10+, pip; `run.sh`/`run.bat` install pygame-ce into
  a local venv on first launch (needs internet once); gameplay is offline.
- Linux standalone: bundles Python 3.10 + pygame-ce + SDL2; verified on a
  glibc 2.35 (Ubuntu 22.04) container with X11. Needs a glibc-compatible
  Linux and X11/Wayland (via XWayland). Not a "zero dependency" build —
  system graphics/sound libs must exist.

## Known limitations
- No online play (local couch play only, per design).
- Ghost fade after elimination is a ~1.5 s non-colliding visual fade;
  the simulation body is removed at death and ghosts never block movement.
