# Controls guide

## Players

- **Player 1 - Keyboard:** W (up), A (left), S (down), D (right)
- **Player 2 - Keyboard:** Arrow keys
- **Players 3-6 - Controllers 1-4:** D-pad. The left analog stick and the
  four face buttons also steer by default; sticks are never required.

Both keyboard players share one keyboard; their keys are independent.

## Menus

- Up/Down to move, Enter/Space to select, Esc to go back.
- Any controller: D-pad to move, first face button to select, Start to go
  back / pause.

## Match setup lobby

Players join by pressing a key on the device they will use:

- **W** joins the WASD player; **Up arrow** joins the arrow-keys player. Once joined, W/S and Up/Down move between rows.
- **Backspace/Delete** removes the focused human player.
- **Controller button 1** joins that controller, **button 2** removes it.
- **B** adds a bot, **X** removes the most recent bot.
- **Tab** moves between option rows, **Left/Right** changes a value
  (arena, size, speed, bot difficulty), **Enter** starts, **Esc** backs.
- Team modes: focus a player row and press **T** to switch teams.

Join/leave only works in the lobby, never mid-match. Classic is the merged
solo entry: start alone, or press B to add bots before starting.

## During a match

- Esc or P (keyboard), Start (controller): pause.
- Pause menu: Resume / Restart / Quit to menu.
- Results: R rematch, Enter back to menu.

## Remapping

Settings > "Remap Player 1/2 keys": press the new key for up, then down,
left, right when prompted. Settings > "Remap controller buttons": press a
button on any controller for each direction. D-pad hat and analog stick
steering can be toggled independently in Settings; sticks are never
required. The mapping lives in `settings.json` (`pad_buttons`,
`pad_use_hat`, `pad_use_stick`) if you prefer editing it directly.

## Controller notes

- Controllers are auto-assigned to slots 1-4 in the order detected; the
  match setup screen shows which controller belongs to which player and
  warns when a slot has nothing connected.
- Connecting or disconnecting a controller during play shows a toast; a
  disconnected pad's player keeps its last direction (classic rules: no
  pausing physics for anyone).
