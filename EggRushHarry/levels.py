"""Level layouts: eight seeded layouts reused for levels 1-16, plus a hand-built boss level (17)."""
import random

from config import (COLS, FLOOR_ROWS, GROUND_ROW, NUM_LAYOUTS, BOSS_LEVEL, OY, TILE, hen_count,
                    LIFT_FROM_LEVEL, LIFT_SPEED, LIFT_DWELL)

SPAWN_COL = 10
JUMP_GAP = 2          # widest floor gap the player can jump across (in tiles)
BOSS_K = NUM_LAYOUTS  # layout index of the boss level

# Per layout: gaps per upper floor, number of floors with a trimmed end, ladders per floor pair.
GAPS = (0, 0, 1, 1, 2, 2, 2, 3)
TRIMS = (0, 0, 0, 1, 1, 2, 2, 3)
LADDERS = (3, 3, 3, 3, 2, 2, 2, 2)

# Boss level: floor 3 is missing, leaving a 6-tile-high hall for Big Momma to roam.
BOSS_FLOORS = (
    "=====..=========.===",
    "====..========.==.==",
    "==========.==.======",
    "." * 20,
    "=" * 20,
)
BOSS_LADDERS = ((0, 1, 3), (0, 1, 11), (0, 1, 18),
                (1, 2, 1), (1, 2, 7), (1, 2, 15),
                (2, 4, 4), (2, 4, 9), (2, 4, 12), (2, 4, 18))
BOSS_ITEMS = ((3, 2), (5, 3), (6, 3), (0, 0), (6, 2))   # (eggs, grain) per floor: 20 eggs, 10 grain
BOSS_SPAWN = (8, 2)                                      # column, floor index


def _connected(floors, ladders):
    """True when every floor cell can be reached from the ground (walking, jumping gaps, ladders)."""
    nodes = {(i, c) for i, row in enumerate(floors) for c, ok in enumerate(row) if ok}
    links = {}
    for u, l, c in ladders:
        links.setdefault((u, c), []).append((l, c))
        links.setdefault((l, c), []).append((u, c))
    start = (len(floors) - 1, SPAWN_COL)
    seen = {start}
    stack = [start]
    while stack:
        i, c = stack.pop()
        nxt = list(links.get((i, c), ()))
        for d in range(1, JUMP_GAP + 2):
            for n in ((i, c + d), (i, c - d)):
                lo, hi = sorted((c, n[1]))
                between = [floors[i][x] for x in range(lo + 1, hi) if 0 <= x < COLS]
                # a hop is fine when the cells strictly between are all empty or all floor
                if not (between and any(between) and not all(between)):
                    nxt.append(n)
        for n in nxt:
            if n in nodes and n not in seen:
                seen.add(n)
                stack.append(n)
    return nodes <= seen


def _scatter(rng, floors, ladders, per_floor, taken=()):
    """Pick item cells (floor index, column) on each floor, away from the cage and ladders."""
    out = []
    for i, counts in enumerate(per_floor):
        cand = []
        for c in range(COLS):
            if not floors[i][c] or (i == 0 and c < 3):
                continue
            if any(c == lc and i in (u, l) for u, l, lc in ladders):
                continue
            if (i, c) in taken:
                continue
            cand.append(c)
        rng.shuffle(cand)
        out.append([(i, c) for c in cand])
    return out


def _fill_items(rng, floors, ladders, eggs_grain):
    pools = _scatter(rng, floors, ladders, eggs_grain)
    eggs, grain = set(), set()
    for pool, (ne, ng) in zip(pools, eggs_grain):
        eggs.update(pool[:ne])
        grain.update(pool[ne:ne + ng])
    return eggs, grain


def _hen_spots(rng, floors, ladders, eggs, order, spawn_col=SPAWN_COL):
    spots = []
    for i in order:
        if i == 4:
            spots.append((4, 3))
            continue
        cand = [c for c in range(COLS)
                if floors[i][c] and (i, c) not in eggs and abs(c - spawn_col) > 2
                and not any(c == lc and i in (u, l) for u, l, lc in ladders)]
        spots.append((i, rng.choice(cand)))
    return spots


def _generate(k):
    rng = random.Random(7000 + k * 31)
    while True:
        floors = [[True] * COLS for _ in FLOOR_ROWS]
        for i in range(4):
            for _ in range(GAPS[k]):
                if i == 0 and GAPS[k] == 0:
                    continue
                w = rng.choice((1, 2))
                c = rng.randint(3 if i == 0 else 1, COLS - 2 - w)
                for x in range(c, c + w):
                    floors[i][x] = False
        for i in rng.sample((1, 2, 3), TRIMS[k]):
            cut = rng.randint(3, 5)
            if rng.random() < 0.5:
                for x in range(cut):
                    floors[i][x] = False
            else:
                for x in range(COLS - cut, COLS):
                    floors[i][x] = False
        for x in range(3):
            floors[0][x] = True            # the cage stands here

        ladders = set()
        ok = True
        for pair in range(4):
            cols = [c for c in range(1, COLS - 1)
                    if floors[pair][c] and floors[pair + 1][c] and not (pair == 0 and c < 3)
                    and all(abs(c - lc) >= 2 for u, l, lc in ladders if l == pair)]
            chosen = []
            rng.shuffle(cols)
            for c in cols:
                if all(abs(c - o) >= 4 for o in chosen):
                    chosen.append(c)
                if len(chosen) == LADDERS[k]:
                    break
            if len(chosen) < 2:
                ok = False
                break
            ladders |= {(pair, pair + 1, c) for c in chosen}
        if not ok or not _connected(floors, ladders):
            continue
        eggs, grain = _fill_items(rng, floors, ladders, ((3, 2), (3, 2), (2, 2), (2, 2), (2, 2)))
        spots = _hen_spots(rng, floors, ladders, eggs, (1, 2, 3, 0, 4, 2, 3))
        return dict(floors=floors, ladders=sorted(ladders), eggs=eggs, grain=grain, hens=spots,
                    spawn=(SPAWN_COL, 4))


def _boss():
    rng = random.Random(1717)
    floors = [[ch == "=" for ch in row] for row in BOSS_FLOORS]
    assert all(len(r) == COLS for r in BOSS_FLOORS), "boss floors must be 20 wide"
    ladders = list(BOSS_LADDERS)
    assert _connected(floors, set(ladders)), "boss level is not connected"
    eggs, grain = _fill_items(rng, floors, ladders, BOSS_ITEMS)
    assert len(eggs) == 20
    spots = _hen_spots(rng, floors, ladders, eggs, (1, 2, 0, 1, 2), BOSS_SPAWN[0])
    return dict(floors=floors, ladders=sorted(ladders), eggs=eggs, grain=grain, hens=spots, spawn=BOSS_SPAWN)


_CACHE = {}


def layout(k):
    if k not in _CACHE:
        _CACHE[k] = _boss() if k == BOSS_K else _generate(k)
    return _CACHE[k]


_LIFT_CACHE = {}


def lift_plan(k):
    """(left column of a two-tile lift shaft, eggs, grain, hen spots) for layout k, or None when no shaft fits.

    The shaft is cut through every floor, leaving a pit at the bottom; items that sat in it move to the nearest free
    spot on the same floor, so every layout keeps its egg count."""
    if k not in _LIFT_CACHE:
        _LIFT_CACHE[k] = None if k == BOSS_K else _plan_lift(k)
    return _LIFT_CACHE[k]


def _plan_lift(k):
    lay = layout(k)
    floors, ladders = lay["floors"], set(lay["ladders"])
    nfl = len(floors)
    rng = random.Random(4100 + k)
    cols = list(range(3, COLS - 4))
    rng.shuffle(cols)
    for c in cols:
        shaft = (c, c + 1)
        if any(lc in shaft for _, _, lc in ladders) or SPAWN_COL in range(c - 1, c + 3):
            continue
        cut = [[ok and x not in shaft for x, ok in enumerate(row)] for row in floors]
        if any(not any(cut[i][:]) for i in range(nfl)):
            continue
        if not _connected(cut, ladders):
            continue
        eggs, grain = set(lay["eggs"]), set(lay["grain"])
        taken = eggs | grain
        ok = True
        for pool in (eggs, grain):
            for i, x in sorted(pool):
                if x not in shaft:
                    continue
                spots = sorted((abs(cx - x), cx) for cx in range(COLS)
                               if cut[i][cx] and (i, cx) not in taken and not (i == 0 and cx < 3)
                               and not any(cx == lc and i in (u, l) for u, l, lc in ladders))
                if not spots:
                    ok = False
                    break
                pool.discard((i, x))
                taken.discard((i, x))
                pool.add((i, spots[0][1]))
                taken.add((i, spots[0][1]))
        hens = []
        for i, x in lay["hens"]:
            if x in shaft:
                x = min((abs(cx - x), cx) for cx in range(COLS)
                        if cut[i][cx] and not any(cx == lc and i in (u, l) for u, l, lc in ladders))[1]
            hens.append((i, x))
        if ok:
            return c, eggs, grain, hens
    return None


class Lift:
    """A platform that shuttles up and down; Harry can ride it and step on or off at each floor."""

    def __init__(self, col):
        self.x0, self.x1 = col * TILE, (col + 2) * TILE
        self.top, self.bot = OY + FLOOR_ROWS[0] * TILE, OY + GROUND_ROW * TILE
        self.y = float(self.bot)
        self.dir = -1
        self.wait = LIFT_DWELL

    def update(self, dt):
        if self.wait > 0:
            self.wait -= dt
            return
        self.y += self.dir * LIFT_SPEED * dt
        if self.y <= self.top:
            self.y, self.dir, self.wait = float(self.top), 1, LIFT_DWELL
        elif self.y >= self.bot:
            self.y, self.dir, self.wait = float(self.bot), -1, LIFT_DWELL


class Level:
    """One playable level (1-17): static geometry plus the collectibles still on the board."""

    def __init__(self, n):
        self.n = n
        self.boss = n == BOSS_LEVEL
        self.k = BOSS_K if self.boss else (n - 1) % NUM_LAYOUTS
        lay = layout(self.k)
        self.floors = {(FLOOR_ROWS[i], c) for i, row in enumerate(lay["floors"]) for c, ok in enumerate(row) if ok}
        self.lifts = []
        self.shafts = []
        self.ladders = set()
        for u, l, c in lay["ladders"]:
            for r in range(FLOOR_ROWS[u], FLOOR_ROWS[l]):
                self.ladders.add((r, c))
        eggs, grain, hens = lay["eggs"], lay["grain"], lay["hens"]
        plan = lift_plan(self.k) if n >= LIFT_FROM_LEVEL and not self.boss else None
        if plan:
            lc, eggs, grain, hens = plan
            self.lifts.append(Lift(lc))
            self.shafts.append((lc, lc + 1))
            self.floors -= {(r, c) for r in FLOOR_ROWS for c in (lc, lc + 1)}
        self.eggs = {(FLOOR_ROWS[i] - 1, c) for i, c in eggs}
        self.grain = {(FLOOR_ROWS[i] - 1, c) for i, c in grain}
        sc, si = lay["spawn"]
        self.spawn = (sc * TILE + TILE / 2, OY + FLOOR_ROWS[si] * TILE)
        spots = hens[:hen_count(n)]
        self.hen_spawns = [(c * TILE + TILE / 2, OY + FLOOR_ROWS[i] * TILE) for i, c in spots]

    def lift_under(self, x, y):
        """The lift Harry's feet at (x, y) rest on, if any."""
        for lf in self.lifts:
            if lf.x0 <= x <= lf.x1 and abs(y - lf.y) <= 5:
                return lf
        return None

    def standing(self, x, y, spread=3):
        """Is there floor under a character whose feet are at (x, y)?"""
        row = round((y - OY) / TILE)
        return ((row, int((x - spread) // TILE)) in self.floors
                or (row, int((x + spread) // TILE)) in self.floors)

    def ladder_span(self, col, row):
        """(top_y, bottom_y) of the ladder containing cell (row, col)."""
        top = bot = row
        while (top - 1, col) in self.ladders:
            top -= 1
        while (bot + 1, col) in self.ladders:
            bot += 1
        return OY + top * TILE, OY + (bot + 1) * TILE

    def egg_pos(self, cell):
        r, c = cell
        return c * TILE + TILE / 2, OY + (r + 1) * TILE
