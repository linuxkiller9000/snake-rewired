# Changelog

## 0.3.2 (2026-11-27) - lobby keyboard fix
- Match-setup lobby: Up/Down and W/S move focus between rows once their
  player has joined (they were reserved as join/leave keys, so the
  keyboard could never leave the lobby or reach START).
- Down and S no longer remove anyone; Backspace/Delete removes the
  focused human player (X still removes bots). Fixes S doing nothing in
  the solo Classic lobby and Down kicking out the arrow player.

## 0.3.1 (2026-11-23) - layout patch
- Six-player timed-mode setup: START button fully inside the panel.
- HUD transparency raised so snakes passing under it stay clearly visible.

## 0.3.0 (2026-11-23) - playtest revision
- Bigger playfield: the right sidebar is gone, the arena fills the window,
  and match status is a compact translucent HUD floating in the top-left
  corner. Elimination notices moved to the top-right.
- Calmer audio: new ~33s generative music loop (slow sine/triangle chord
  progression with a varied legato pentatonic melody) replacing the fast
  square-wave loop; SFX softened from square to triangle/sine.
- Device-led lobby: press W to join as the WASD player (S to leave),
  Up/Down arrows for the second keyboard player, controller button 1/2 to
  join/leave a pad. B adds a bot, X removes one. Tab navigates options.
- Classic is now the single solo entry: play alone or add bots in setup
  (the separate Solo vs Bots menu button is gone).

## 0.2.0 (2026-11-23) - polish and verification
- Smooth interpolated movement between grid cells (per-segment lerp,
  mid-tick visually verified).
- Eliminated snakes leave only a ~1.5s fading ghost; the simulation body is
  fully removed at death.
- In-game controller button remapping + D-pad/stick toggles in Settings.
- Garage head cycling skips locked styles.
- Nokia monochrome mode (solo) now covers food too.
- Fair same-tick tie ranking (elimination tick, then score).
- Mode verification: Score Race, Team Survival and pause menu scripted
  end-to-end with screenshots.

## 0.1.0 (2026-11-23) - first milestone build
- Fixed-grid simulation separated from rendering (pygame-free core).
- Classic collision rules: wall/obstacle/self/body/head-on/swap deaths,
  simultaneous resolution, vacating-tail rule, documented in core/rules.py.
- Five modes: Classic Solo, Solo vs Bots, Battle Arena, Score Race,
  Team Survival.
- Six players in one shared arena: WASD + arrows + four controllers;
  hotplug feedback, per-slot assignment, keyboard remapping.
- AI bots: Easy / Normal / Hard (BFS routing, trap avoidance, contest play).
- Five arena themes x three sizes, optional symmetric obstacle patterns.
- Food: normal/bonus/golden/speed/slow with expiry and effects.
- Garage customization: colors, patterns, head styles, unlockable skins.
- Procedural SFX + chiptune music, volume controls, mute.
- JSON settings/save with atomic writes and corruption recovery.
- Statistics, achievements, match history, high scores.
- 37 automated tests + scripted six-player headless runtime test with
  screenshot capture.
