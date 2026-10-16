"""Level layouts: eight seeded layouts, each guaranteed solvable, reused for levels 1-16."""
import random

from config import COLS, FLOOR_ROWS, GROUND_ROW, NUM_LAYOUTS, OY, TILE, hen_count

SPAWN_COL = 10
JUMP_GAP = 2          # widest floor gap the player can jump across (in tiles)

# Per layout: gaps per upper floor, number of floors with a trimmed end, ladders per floor pair.
GAPS = (0, 0, 1, 1, 2, 2, 2, 3)
TRIMS = (0, 0, 0, 1, 1, 2, 2, 3)
LADDERS = (3, 3, 3, 3, 2, 2, 2, 2)


def _connected(floors, ladders):
    """True when every floor cell can be reached from the ground (walking, jumping gaps, ladders)."""
    nodes = {(i, c) for i, row in enumerate(floors) for c, ok in enumerate(row) if ok}
    start = (len(floors) - 1, SPAWN_COL)
    seen = {start}
    stack = [start]
    while stack:
        i, c = stack.pop()
        nxt = []
        for d in range(1, JUMP_GAP + 2):
            nxt += [(i, c + d), (i, c - d)]
        nxt += [(i + 1, c), (i - 1, c)]
        for n in nxt:
            if n not in nodes or n in seen:
                continue
            ni, nc = n
            if ni == i:
                lo, hi = sorted((c, nc))
                # a horizontal hop is fine when the cells strictly between are all empty or all floor
                between = [floors[i][x] for x in range(lo + 1, hi)]
                if between and any(between) and not all(between):
                    continue
            elif (min(i, ni), c) not in ladders:
                continue
            seen.add(n)
            stack.append(n)
    return nodes <= seen


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
        for i in rng.sample((1, 2, 3), TRIMS[k] if TRIMS[k] <= 3 else 3):
            cut = rng.randint(3, 5)
            if rng.random() < 0.5:
                for x in range(cut):
                    floors[i][x] = False
            else:
                for x in range(COLS - cut, COLS):
                    floors[i][x] = False
        for x in range(3):
            floors[0][x] = True            # the cage stands here

        ladders = set()            # (pair index, column)
        ok = True
        for pair in range(4):
            cols = [c for c in range(1, COLS - 1)
                    if floors[pair][c] and floors[pair + 1][c] and not (pair == 0 and c < 3)
                    and all(abs(c - pc) >= 2 for pp, pc in ladders if pp == pair - 1)]
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
            ladders |= {(pair, c) for c in chosen}
        if not ok or not _connected(floors, ladders):
            continue

        ladder_cols = {}
        for pair, c in ladders:
            ladder_cols.setdefault(pair, set()).add(c)

        def cells(i):
            out = []
            for c in range(COLS):
                if not floors[i][c] or (i == 0 and c < 3):
                    continue
                if c in ladder_cols.get(i, ()) or c in ladder_cols.get(i - 1, ()):
                    continue
                out.append(c)
            return out

        eggs, grain = set(), set()
        for i, (ne, ng) in enumerate(((3, 2), (3, 2), (2, 2), (2, 2), (2, 2))):
            cand = cells(i)
            rng.shuffle(cand)
            for c in cand[:ne]:
                eggs.add((i, c))
            for c in cand[ne:ne + ng]:
                grain.add((i, c))

        spots = []
        for i in (1, 2, 3, 0, 4, 2, 3):
            if i == 4:
                spots.append((4, 3))
                continue
            cand = [c for c in cells(i) if (i, c) not in eggs]
            spots.append((i, rng.choice(cand)))
        return dict(floors=floors, ladders=sorted(ladders), eggs=eggs, grain=grain, hens=spots)


_CACHE = {}


def layout(k):
    if k not in _CACHE:
        _CACHE[k] = _generate(k)
    return _CACHE[k]


class Level:
    """One playable level (1-16): static geometry plus the collectibles still on the board."""

    def __init__(self, n):
        self.n = n
        self.k = (n - 1) % NUM_LAYOUTS
        lay = layout(self.k)
        self.floors = {(FLOOR_ROWS[i], c) for i, row in enumerate(lay["floors"]) for c, ok in enumerate(row) if ok}
        self.ladders = set()
        for c_pair in lay["ladders"]:
            pair, c = c_pair
            for r in range(FLOOR_ROWS[pair], FLOOR_ROWS[pair + 1]):
                self.ladders.add((r, c))
        self.eggs = {(FLOOR_ROWS[i] - 1, c) for i, c in lay["eggs"]}
        self.grain = {(FLOOR_ROWS[i] - 1, c) for i, c in lay["grain"]}
        self.spawn = (SPAWN_COL * TILE + TILE / 2, OY + GROUND_ROW * TILE)
        spots = lay["hens"][:hen_count(n)]
        self.hen_spawns = [(c * TILE + TILE / 2, OY + FLOOR_ROWS[i] * TILE) for i, c in spots]

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
