"""Game mode definitions. Pure Python, no pygame."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModeConfig:
    key: str
    title: str
    description: str
    min_players: int
    max_players: int
    allow_bots: bool
    teams: bool
    timed: bool                 # match has a configurable time limit
    default_duration: int       # seconds, when timed (0 = untimed)
    food_normal_target: int
    food_special_chance: float
    food_specials: tuple
    allow_obstacles: bool
    classic_ramp: bool          # Nokia-style speed increase with score
    survival_win: bool          # last snake alive wins
    score_win: bool             # highest score wins at the end


MODES = {
    "classic": ModeConfig(
        key="classic",
        title="Classic",
        description="Faithful Nokia-style Snake. Play alone, or press B in "
                    "setup to add bots. Growing speed, high-score chase.",
        min_players=1, max_players=6, allow_bots=True, teams=False,
        timed=False, default_duration=0,
        food_normal_target=1, food_special_chance=0.0, food_specials=(),
        allow_obstacles=False, classic_ramp=True,
        survival_win=False, score_win=True,
    ),
    "solo_bots": ModeConfig(
        key="solo_bots",
        title="Solo vs Bots",
        description="You against configurable AI opponents on a shared arena.",
        min_players=2, max_players=6, allow_bots=True, teams=False,
        timed=False, default_duration=0,
        food_normal_target=2, food_special_chance=0.02,
        food_specials=("bonus", "golden", "speed", "slow"),
        allow_obstacles=True, classic_ramp=False,
        survival_win=True, score_win=False,
    ),
    "battle": ModeConfig(
        key="battle",
        title="Battle Arena",
        description="2-6 players, one shared arena. Last snake alive wins.",
        min_players=2, max_players=6, allow_bots=True, teams=False,
        timed=False, default_duration=0,
        food_normal_target=3, food_special_chance=0.03,
        food_specials=("bonus", "golden", "speed", "slow"),
        allow_obstacles=True, classic_ramp=False,
        survival_win=True, score_win=False,
    ),
    "score_race": ModeConfig(
        key="score_race",
        title="Score Race",
        description="Highest score when the clock runs out wins. "
                    "Eliminated players stay out.",
        min_players=2, max_players=6, allow_bots=True, teams=False,
        timed=True, default_duration=120,
        food_normal_target=3, food_special_chance=0.05,
        food_specials=("bonus", "golden", "speed", "slow"),
        allow_obstacles=True, classic_ramp=False,
        survival_win=False, score_win=True,
    ),
    "team_survival": ModeConfig(
        key="team_survival",
        title="Team Survival",
        description="Two teams. Teammates still collide with each other. "
                    "Eliminate the other team or outscore them.",
        min_players=2, max_players=6, allow_bots=True, teams=True,
        timed=True, default_duration=180,
        food_normal_target=3, food_special_chance=0.03,
        food_specials=("bonus", "golden", "speed", "slow"),
        allow_obstacles=True, classic_ramp=False,
        survival_win=True, score_win=True,  # survival first, score tiebreak
    ),
}

MODE_KEYS = tuple(MODES.keys())

SPEEDS = {
    "relaxed": 0.140,
    "normal": 0.100,
    "fast": 0.070,
}

# Classic solo speed ramp: interval shrinks per food eaten, to a floor.
CLASSIC_RAMP_STEP = 0.0025
CLASSIC_RAMP_FLOOR = 0.055

DURATION_OPTIONS = (60, 120, 180, 300)
