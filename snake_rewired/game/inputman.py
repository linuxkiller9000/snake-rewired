"""Input system: keyboard sharing, gamepads, remapping, hotplug.

Six human players: P1 keyboard WASD, P2 keyboard arrows, P3-P6 controllers
1-4. Keyboard is a shared device: both keyboard players read the same event
stream filtered by their own key mapping, so they never block each other.

pygame is imported lazily inside device-touching code so the core and the
tests that do not need a display stay import-safe without SDL.
"""

from ..core.geometry import UP, DOWN, LEFT, RIGHT, NAME_DIRS

ACTIONS = ("up", "down", "left", "right")
ACTION_DIRS = {"up": UP, "down": DOWN, "left": LEFT, "right": RIGHT}


class HumanController:
    """Queued-direction source fed by an input manager each frame."""

    def __init__(self):
        self._queued = None

    def push(self, direction):
        self._queued = direction

    def next_direction(self, snake, match):
        d, self._queued = self._queued, None
        return d


class KeyboardDevice:
    """Maps key names to (player, action) using the settings mapping."""

    def __init__(self, settings):
        self.settings = settings

    def lookup(self, key_name):
        for player_index, setting_key in ((0, "keys_p1"), (1, "keys_p2")):
            mapping = self.settings.get(setting_key, {})
            for action, name in mapping.items():
                if name == key_name and action in ACTION_DIRS:
                    return player_index, action
        return None

    def remap(self, player_index, action, key_name):
        setting_key = "keys_p1" if player_index == 0 else "keys_p2"
        mapping = dict(self.settings.get(setting_key, {}))
        # Drop any other action already using this key.
        for act, name in list(mapping.items()):
            if name == key_name:
                del mapping[act]
        mapping[action] = key_name
        self.settings.set(setting_key, mapping)


class PadMapping:
    """Direction mapping for one gamepad: hat, optional stick, buttons."""

    def __init__(self, settings):
        self.settings = settings

    def direction_from_state(self, joy):
        """Read a pygame joystick-like object; returns a direction or None.

        Priority: D-pad hat, then configured buttons, then left stick.
        Works with any object exposing get_hat/get_button/get_axis so tests
        can inject virtual pads.
        """
        if self.settings.get("pad_use_hat", True):
            try:
                hx, hy = joy.get_hat(0)
            except Exception:
                hx, hy = 0, 0
            if hy > 0:
                return UP
            if hy < 0:
                return DOWN
            if hx < 0:
                return LEFT
            if hx > 0:
                return RIGHT
        buttons = self.settings.get("pad_buttons", {})
        for action, idx in buttons.items():
            try:
                if joy.get_button(int(idx)):
                    return ACTION_DIRS[action]
            except Exception:
                continue
        if self.settings.get("pad_use_stick", True):
            try:
                ax, ay = joy.get_axis(0), joy.get_axis(1)
            except Exception:
                ax, ay = 0.0, 0.0
            if abs(ay) > 0.5 and abs(ay) >= abs(ax):
                return UP if ay < 0 else DOWN
            if abs(ax) > 0.5:
                return LEFT if ax < 0 else RIGHT
        return None


class InputManager:
    """Owns devices and routes intents to per-player HumanControllers.

    player_devices: player index (0-5) -> ("kb", 0|1) or ("pad", slot 0-3)
    pad_slots: slot -> live joystick instance id (assignment screen edits)
    """

    def __init__(self, settings):
        self.settings = settings
        self.keyboard = KeyboardDevice(settings)
        self.pad_mapping = PadMapping(settings)
        self.controllers = {}        # player index -> HumanController
        self.player_devices = {}     # player index -> device tuple
        self.pad_slots = {0: None, 1: None, 2: None, 3: None}
        self._joys = {}              # pygame instance id -> joystick obj
        self.pygame = None

    # -- device lifecycle -------------------------------------------------
    def init_pygame(self, pygame_module):
        self.pygame = pygame_module
        pygame_module.joystick.init()
        self._scan_pads()

    def _scan_pads(self):
        pg = self.pygame
        if pg is None:
            return
        self._joys = {}
        for i in range(pg.joystick.get_count()):
            joy = pg.joystick.Joystick(i)
            joy.init()
            self._joys[joy.get_instance_id()] = joy
        # Fill empty slots with newly found pads, keep existing assignments.
        used = {v for v in self.pad_slots.values() if v is not None}
        for iid in self._joys:
            if iid in used:
                continue
            for slot in range(4):
                if self.pad_slots[slot] is None:
                    self.pad_slots[slot] = iid
                    used.add(iid)
                    break

    def handle_hotplug(self, event):
        pg = self.pygame
        if pg is None:
            return None
        if event.type == pg.JOYDEVICEREMOVED:
            iid = event.instance_id
            self._joys.pop(iid, None)
            for slot, cur in self.pad_slots.items():
                if cur == iid:
                    self.pad_slots[slot] = None
            return ("disconnected", iid)
        if event.type == pg.JOYDEVICEADDED:
            self._scan_pads()
            return ("connected", None)
        return None

    def pad_name(self, slot):
        iid = self.pad_slots.get(slot)
        joy = self._joys.get(iid) if iid is not None else None
        return joy.get_name() if joy else None

    # -- player wiring ------------------------------------------------------
    def bind_player(self, player_index, device):
        self.player_devices[player_index] = device
        self.controllers.setdefault(player_index, HumanController())

    def unbind_player(self, player_index):
        self.player_devices.pop(player_index, None)

    def controller_for(self, player_index):
        return self.controllers.setdefault(player_index, HumanController())

    # -- frame pump ---------------------------------------------------------
    def handle_keydown(self, key_name):
        hit = self.keyboard.lookup(key_name)
        if hit is None:
            return False
        player_index, action = hit
        ctl = self.controllers.get(player_index)
        if ctl is not None and self.player_devices.get(player_index, ("kb",))[0] == "kb":
            ctl.push(ACTION_DIRS[action])
            return True
        return False

    def pump_pads(self):
        """Call once per frame: reads pad states and pushes intents."""
        for player_index, device in list(self.player_devices.items()):
            if device[0] != "pad":
                continue
            iid = self.pad_slots.get(device[1])
            joy = self._joys.get(iid) if iid is not None else None
            if joy is None:
                continue
            d = self.pad_mapping.direction_from_state(joy)
            if d is not None:
                self.controllers[player_index].push(d)


class VirtualPad:
    """Test double for a pygame joystick (hat + buttons + axis)."""

    def __init__(self, name="Virtual Pad"):
        self._name = name
        self._hat = (0, 0)
        self._buttons = {}
        self._axes = (0.0, 0.0)

    def get_name(self):
        return self._name

    def get_hat(self, i):
        return self._hat

    def set_hat(self, value):
        self._hat = value

    def get_button(self, i):
        return self._buttons.get(i, 0)

    def set_button(self, i, value):
        self._buttons[i] = value

    def get_axis(self, i):
        return self._axes[i]

    def set_axis(self, i, value):
        axes = list(self._axes)
        axes[i] = value
        self._axes = tuple(axes)
