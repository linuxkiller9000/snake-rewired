"""Settings and save-game persistence. JSON, atomic writes, corruption-safe.

Save location:
  Linux:   ~/.local/share/snake-rewired/save.json, ~/.config/snake-rewired/settings.json
  Windows: %APPDATA%/SnakeRewired/save.json + settings.json
Override with SNAKE_REWIRED_HOME (used by tests).
"""

import json
import os
import shutil
import sys
import tempfile


def data_dir():
    override = os.environ.get("SNAKE_REWIRED_HOME")
    if override:
        return override
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "SnakeRewired")
    if os.environ.get("XDG_DATA_HOME"):
        return os.path.join(os.environ["XDG_DATA_HOME"], "snake-rewired")
    return os.path.join(os.path.expanduser("~"), ".local", "share",
                        "snake-rewired")


def config_dir():
    override = os.environ.get("SNAKE_REWIRED_HOME")
    if override:
        return override
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "SnakeRewired")
    if os.environ.get("XDG_CONFIG_HOME"):
        return os.path.join(os.environ["XDG_CONFIG_HOME"], "snake-rewired")
    return os.path.join(os.path.expanduser("~"), ".config", "snake-rewired")


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        # Corrupted: move aside, never crash.
        try:
            shutil.copy2(path, path + ".corrupt")
        except OSError:
            pass
        return None


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


DEFAULT_SETTINGS = {
    "master_volume": 0.8,
    "music_volume": 0.6,
    "sfx_volume": 0.9,
    "muted": False,
    "fullscreen": False,
    "vsync": True,
    "show_grid": True,
    "high_contrast": False,
    "speed": "normal",
    "arena_theme": "neon",
    "arena_size": "medium",
    "obstacles": True,
    "match_duration": 120,
    "keys_p1": {"up": "w", "down": "s", "left": "a", "right": "d"},
    "keys_p2": {"up": "up", "down": "down", "left": "left", "right": "right"},
    "pad_buttons": {"up": 12, "down": 13, "left": 14, "right": 15},
    "pad_use_hat": True,
    "pad_use_stick": True,
    "players": [
        {"color": 0, "pattern": "solid", "head": "classic"},
        {"color": 1, "pattern": "solid", "head": "classic"},
        {"color": 2, "pattern": "solid", "head": "classic"},
        {"color": 3, "pattern": "solid", "head": "classic"},
        {"color": 4, "pattern": "solid", "head": "classic"},
        {"color": 5, "pattern": "solid", "head": "classic"},
    ],
}

DEFAULT_SAVE = {
    "high_scores": {},          # mode -> int
    "matches_played": 0,
    "wins": 0,
    "losses": 0,
    "food_collected": 0,
    "longest_snake": 0,
    "best_survival_seconds": 0.0,
    "total_play_seconds": 0.0,
    "match_history": [],        # newest first, capped at 20
    "achievements": {},         # key -> unlock ISO date string
    "unlocked_skins": ["solid"],
}


class Settings:
    def __init__(self):
        self._path = os.path.join(config_dir(), "settings.json")
        self._data = json.loads(json.dumps(DEFAULT_SETTINGS))
        loaded = _read_json(self._path)
        if isinstance(loaded, dict):
            self._merge(self._data, loaded)

    @staticmethod
    def _merge(base, extra):
        for k, v in extra.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                Settings._merge(base[k], v)
            else:
                base[k] = v

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def save(self):
        _write_json(self._path, self._data)


class SaveGame:
    def __init__(self):
        self._path = os.path.join(data_dir(), "save.json")
        self._data = json.loads(json.dumps(DEFAULT_SAVE))
        loaded = _read_json(self._path)
        if isinstance(loaded, dict):
            Settings._merge(self._data, loaded)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def record_match(self, result, player_is_winner):
        d = self._data
        d["matches_played"] += 1
        if player_is_winner:
            d["wins"] += 1
        else:
            d["losses"] += 1
        mode = result["mode"]
        best_food = max((r["food"] for r in result["rankings"]), default=0)
        best_len = max((r["length"] for r in result["rankings"]), default=0)
        best_surv = max((r["survival_ticks"] for r in result["rankings"]),
                        default=0)
        d["food_collected"] += sum(r["food"] for r in result["rankings"])
        d["longest_snake"] = max(d["longest_snake"], best_len)
        surv_seconds = best_surv * 0.1
        d["best_survival_seconds"] = max(d["best_survival_seconds"],
                                         round(surv_seconds, 1))
        d["total_play_seconds"] = round(
            d["total_play_seconds"] + result.get("duration", 0.0), 1)
        top = max((r["score"] for r in result["rankings"]), default=0)
        d["high_scores"][mode] = max(d["high_scores"].get(mode, 0), top)
        d["match_history"].insert(0, {
            "mode": mode,
            "winner": result.get("winner_name"),
            "winning_team": result.get("winning_team"),
            "players": len(result["rankings"]),
            "top_score": top,
        })
        del d["match_history"][20:]
        self._check_achievements(result)
        self.save()

    def _check_achievements(self, result):
        ach = self._data["achievements"]
        skins = self._data["unlocked_skins"]

        def grant(key, skin=None):
            ach.setdefault(key, "unlocked")
            if skin and skin not in skins:
                skins.append(skin)

        d = self._data
        if d["matches_played"] >= 1:
            grant("first_match")
        if d["wins"] >= 1:
            grant("first_win", "striped")
        if d["wins"] >= 10:
            grant("champion", "golden")
        if d["food_collected"] >= 100:
            grant("glutton", "dotted")
        if d["food_collected"] >= 500:
            grant("feast", "circuit")
        if d["longest_snake"] >= 25:
            grant("centipede", "scaled")
        if d["best_survival_seconds"] >= 120:
            grant("survivor", "visor")
        if result.get("mode") == "team_survival" and result.get(
                "winning_team") is not None:
            grant("team_player")

    def save(self):
        _write_json(self._path, self._data)
