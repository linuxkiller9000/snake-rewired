"""Classic collision rules and simultaneous step resolution.

Documented rule set (applied identically to humans and AI):

1. A snake dies if its head leaves the arena or enters an obstacle cell.
2. A snake dies if its head enters a cell that was occupied at the start of
   the step by ANY snake body (its own or another's), EXCEPT the tail cell
   of a moving snake that is not growing this step (that tail moves away).
3. Head-on: if two or more snakes move their heads into the SAME cell in
   the same step, ALL of them die.
4. Head swap: if snake A's head enters snake B's current head cell while
   snake B's head enters snake A's current head cell in the same step,
   BOTH die (they cannot pass through each other).
5. Deaths are computed from the pre-step state and applied simultaneously:
   a snake killed by a wall still blocks others this step; no ordering
   advantage exists for any player.
6. Eating is resolved after movement: a snake whose head lands on food
   eats it, grows (its tail does not move away next steps until growth is
   consumed) and scores. A snake does not vacate its tail on a step where
   it eats.
"""

from collections import defaultdict

from .geometry import add
from .food import FOOD_INFO, SPEED_EFFECT_TICKS, SLOW_EFFECT_TICKS

EFFECT_DURATIONS = {"speed": SPEED_EFFECT_TICKS, "slow": SLOW_EFFECT_TICKS}


def resolve_step(moving, snakes, arena, food_mgr, tick, events):
    """Resolve one simultaneous movement step for the snakes in `moving`.

    `snakes` is every snake in the match (alive or dead). Mutates state.
    Appends event tuples to `events`:
      ("death", snake, reason)   reason in wall|obstacle|self|body|headon|swap
      ("eat", snake, food_item)
    """
    moving = [s for s in moving if s.alive]
    if not moving:
        return

    # Phase 0: apply queued turns (reversal-safe).
    for s in moving:
        s.consume_turn()

    targets = {s.sid: add(s.head, s.direction) for s in moving}
    by_sid = {s.sid: s for s in moving}

    deaths = {}  # sid -> reason

    # Phase 1: walls and obstacles.
    for s in moving:
        t = targets[s.sid]
        if not arena.in_bounds(t):
            deaths[s.sid] = "wall"
        elif t in arena.obstacles:
            deaths[s.sid] = "obstacle"

    # Phase 2: head-on into the same target cell.
    cell_claims = defaultdict(list)
    for sid, t in targets.items():
        cell_claims[t].append(sid)
    for t, sids in cell_claims.items():
        if len(sids) > 1:
            for sid in sids:
                deaths[sid] = "headon"

    # Phase 3: head swaps (A->B.head while B->A.head).
    for s in moving:
        t = targets[s.sid]
        for other in moving:
            if other.sid == s.sid:
                continue
            if t == other.head and targets[other.sid] == s.head:
                deaths[s.sid] = "swap"

    # Phase 4: body collisions against pre-step occupancy.
    # A moving snake that will eat this step does not vacate its tail;
    # eating is known now because targets and deaths-from-walls are known.
    eats = {}
    for s in moving:
        if s.sid in deaths:
            eats[s.sid] = False
        else:
            eats[s.sid] = food_mgr.at(targets[s.sid]) is not None

    blocked = set()
    owners = {}
    for sn in snakes:
        if not sn.alive:
            continue
        cells = list(sn.cells)
        if (sn.sid in by_sid and sn.growth == 0 and not eats.get(sn.sid, False)
                and deaths.get(sn.sid) is None):
            # Moving, not growing, not eating: tail cell is vacated.
            cells = cells[:-1]
        for c in cells:
            blocked.add(c)
            owners[c] = sn.sid

    for s in moving:
        if s.sid in deaths:
            continue
        t = targets[s.sid]
        if t in blocked:
            owner = owners.get(t)
            deaths[s.sid] = "self" if owner == s.sid else "body"

    # Phase 5: apply deaths simultaneously, then move survivors.
    for sid, reason in sorted(deaths.items()):
        s = by_sid[sid]
        s.eliminate(tick, reason)
        events.append(("death", s, reason))

    for s in moving:
        if not s.alive:
            continue
        t = targets[s.sid]
        s.cells.appendleft(t)
        item = food_mgr.at(t)
        if item is not None:
            info = FOOD_INFO[item.kind]
            s.score += info["score"]
            s.food_eaten += 1
            s.growth += info["growth"]
            effect = info["effect"]
            if effect:
                s.apply_effect(effect, EFFECT_DURATIONS[effect])
            food_mgr.remove(t)
            events.append(("eat", s, item))
        if s.growth > 0:
            s.growth -= 1
        else:
            s.cells.pop()
