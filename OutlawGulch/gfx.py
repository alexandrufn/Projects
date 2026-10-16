"""Procedural pixel-art graphics for Outlaw Gulch: characters, items and scrolling stage backdrops.

Everything is drawn in code at the logical 320x256 resolution, so the game ships without image files.
"""
import math
import random

import pygame

from config import W, H, OY, PLAY_H

OUT = (26, 16, 24)
SKIN, SKIN_D = (240, 190, 150), (200, 140, 104)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _r(s, c, x, y, w, h):
    pygame.draw.rect(s, c, (x, y, w, h))


def outline(s, color=OUT):
    w, h = s.get_size()
    out = _surf(w + 2, h + 2)
    sil = pygame.mask.from_surface(s, 40).to_surface(setcolor=color + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, (dx, dy))
    out.blit(s, (1, 1))
    return out


def flash(s, amount=150):
    """A copy of a sprite washed out towards white (hit feedback)."""
    f = s.copy()
    f.fill((amount, amount, amount, 0), special_flags=pygame.BLEND_RGB_ADD)
    return f


_fonts = {}


def text(surf, s, size, pos, color=(255, 255, 255), anchor="center", shadow=True):
    f = _fonts.get(size)
    if f is None:
        f = _fonts[size] = pygame.font.Font(None, size)
    img = f.render(s, False, color)
    r = img.get_rect()
    setattr(r, anchor, pos)
    if shadow:
        surf.blit(f.render(s, False, (24, 14, 22)), r.move(1, 1))
    surf.blit(img, r)
    return r


# ----------------------------------------------------------------------------
# Characters
# ----------------------------------------------------------------------------
PALETTES = {
    "hank": dict(hat=(30, 24, 22), band=(214, 40, 44), shirt=(224, 168, 128), vest=(224, 168, 128),
                 pants=(76, 92, 60), boot=(40, 34, 30), mask=None, style="band", bare=True),
    "carl": dict(hat=(96, 70, 44), band=(40, 80, 40), shirt=(70, 110, 62), vest=(52, 86, 48),
                 pants=(84, 104, 66), boot=(36, 30, 26), mask=None, style="buzz", bare=True, tank=True),
    "outlaw": dict(hat=(46, 42, 54), band=(150, 40, 40), shirt=(184, 60, 60), vest=(120, 40, 44),
                   pants=(88, 84, 100), boot=(50, 40, 40), mask=(206, 50, 50)),
    "gunman": dict(hat=(196, 156, 96), band=(120, 80, 40), shirt=(92, 132, 84), vest=(70, 104, 66),
                   pants=(110, 80, 56), boot=(60, 40, 30), mask=(70, 110, 190)),
    "dynamite": dict(hat=(180, 60, 40), band=(250, 210, 80), shirt=(238, 148, 56), vest=(190, 100, 40),
                     pants=(70, 62, 54), boot=(46, 36, 30), mask=(250, 210, 80)),
    "jack": dict(hat=(30, 30, 38), band=(200, 170, 60), shirt=(60, 60, 80), vest=(30, 30, 40),
                 pants=(40, 40, 50), boot=(24, 24, 30), mask=None),
    "lola": dict(hat=(180, 40, 90), band=(250, 210, 90), shirt=(220, 80, 130), vest=(120, 30, 70),
                 pants=(60, 40, 80), boot=(40, 24, 40), mask=None),
    "mike": dict(hat=(100, 100, 110), band=(60, 60, 70), shirt=(130, 134, 150), vest=(80, 84, 100),
                 pants=(70, 74, 90), boot=(40, 40, 50), mask=(60, 60, 70)),
    "cobra": dict(hat=(40, 120, 80), band=(220, 200, 60), shirt=(50, 150, 100), vest=(30, 90, 64),
                  pants=(40, 70, 60), boot=(24, 40, 34), mask=(220, 200, 60)),
    "diablo": dict(hat=(150, 20, 30), band=(250, 200, 60), shirt=(200, 30, 40), vest=(90, 14, 24),
                   pants=(40, 30, 40), boot=(20, 16, 20), mask=None),
}


def humanoid(pal, back=False, step=0, aim=0):
    """16x22 character. back=True shows the back (player), else the front (enemies)."""
    s = _surf(16, 22)
    ly = (15, 14) if step == 0 else (14, 15)
    for lx, y in ((4, ly[0]), (9, ly[1])):
        _r(s, pal["pants"], lx, y, 3, 22 - 2 - y)
        _r(s, pal["boot"], lx, 20, 3, 2)
    _r(s, pal["shirt"], 3, 8, 10, 8)
    _r(s, pal["vest"], 3, 9, 4, 7)
    _r(s, pal["vest"], 9, 9, 4, 7)
    if not back:
        _r(s, shade(pal["vest"], 0.7), 7, 9, 2, 7)
    bare = pal.get("bare")
    for ax in ((0, 13) if bare else (1, 13)):
        if bare:
            _r(s, SKIN, ax, 8, 3, 7)
            _r(s, SKIN_D, ax + (2 if ax == 0 else 0), 9, 1, 5)
            _r(s, SKIN, ax, 15, 3, 1)
        else:
            _r(s, pal["shirt"], ax, 9, 2, 5)
            _r(s, SKIN, ax, 14, 2, 2)
    gx = 13 + aim
    if back:
        _r(s, (70, 70, 80), gx, 5, 2, 7)
        _r(s, (170, 170, 190), gx, 4, 2, 2)
    else:
        _r(s, (70, 70, 80), 13, 13, 2, 6)
        _r(s, (170, 170, 190), 13, 18, 2, 2)
    _r(s, SKIN, 5, 3, 6, 6)
    if back:
        _r(s, (96, 60, 34), 5, 6, 6, 3)
    else:
        _r(s, (30, 20, 30), 6, 5, 1, 2)
        _r(s, (30, 20, 30), 9, 5, 1, 2)
        if pal["mask"]:
            _r(s, pal["mask"], 5, 7, 6, 3)
        else:
            _r(s, SKIN_D, 7, 8, 2, 1)
    style = pal.get("style")
    if style == "band":                                   # bare-chested hero with a headband
        _r(s, pal["hat"], 4, 1, 8, 4)
        _r(s, pal["hat"], 3, 3, 1, 4)
        _r(s, pal["hat"], 12, 3, 1, 4)
        _r(s, pal["band"], 4, 4, 8, 2)
        _r(s, pal["band"], 12, 5, 2, 1)
        _r(s, pal["band"], 13, 6, 2, 2)
        if not back:
            _r(s, SKIN_D, 6, 7, 4, 1)
    elif style == "buzz":                                 # buzz cut and camo face paint
        _r(s, pal["hat"], 5, 1, 6, 3)
        _r(s, pal["hat"], 4, 3, 1, 2)
        _r(s, pal["hat"], 11, 3, 1, 2)
        if not back:
            _r(s, (40, 70, 40), 5, 5, 6, 1)
            _r(s, (40, 70, 40), 5, 7, 2, 2)
            _r(s, (40, 70, 40), 9, 7, 2, 2)
    else:
        _r(s, pal["hat"], 4, 0, 8, 4)
        _r(s, pal["band"], 4, 3, 8, 1)
        _r(s, pal["hat"], 1, 3, 14, 2)
        _r(s, shade(pal["hat"], 0.7), 1, 4, 14, 1)
    if pal.get("bare"):
        for i in range(6):                                # chest muscles / straps
            _r(s, SKIN_D, 5 + (i % 2) * 4, 9 + i, 1, 1) if not pal.get("tank") else None
        if pal.get("tank"):
            _r(s, pal["shirt"], 4, 8, 3, 3)
            _r(s, pal["shirt"], 9, 8, 3, 3)
            for yy in range(3):
                _r(s, (60, 50, 40), 4 + yy * 2, 11 + yy * 2, 3, 1)  # ammo belt
        else:
            for i in range(7):                            # bandolier across the chest
                _r(s, (110, 80, 50), 3 + i, 9 + i, 2, 1)
            _r(s, (230, 200, 90), 5, 11, 1, 1)
            _r(s, (230, 200, 90), 8, 14, 1, 1)
    return outline(s)


def make_horse(step):
    s = _surf(20, 36)
    hide, dark = (146, 92, 58), (96, 58, 38)
    leg = [(3, 14, 3, 7), (14, 14, 3, 7), (3, 24, 3, 7), (14, 24, 3, 7)]
    for i, (x, y, w, h) in enumerate(leg):
        off = 2 if (i + step) % 2 else -1
        _r(s, dark, x, y + off, w, h)
    pygame.draw.ellipse(s, hide, (3, 6, 14, 24))
    pygame.draw.ellipse(s, shade(hide, 1.2), (5, 8, 6, 12))
    _r(s, dark, 8, 0, 4, 8)                                # tail
    pygame.draw.ellipse(s, hide, (6, 26, 8, 9))            # head
    _r(s, (30, 20, 20), 7, 32, 2, 2)
    _r(s, (30, 20, 20), 11, 32, 2, 2)
    _r(s, dark, 9, 24, 2, 5)                               # mane
    return outline(s)


def make_rider(step):
    horse = make_horse(step)
    rider = humanoid(PALETTES["outlaw"], back=False, step=step)
    out = _surf(22, 38)
    out.blit(horse, (0, 2))
    out.blit(rider, (2, 0))
    return out


def make_boss(pal_key, scale=2, step=0):
    base = humanoid(PALETTES[pal_key], back=False, step=step)
    return pygame.transform.scale(base, (base.get_width() * scale, base.get_height() * scale))


# ----------------------------------------------------------------------------
# Items and small sprites
# ----------------------------------------------------------------------------
def _badge(inner):
    s = _surf(14, 14)
    pygame.draw.circle(s, (250, 214, 90), (7, 7), 7)
    pygame.draw.circle(s, (196, 140, 40), (7, 7), 7, 1)
    pygame.draw.circle(s, (120, 70, 30), (7, 7), 5)
    inner(s)
    return outline(s)


def make_items():
    def boots(s):
        _r(s, (240, 220, 180), 5, 3, 3, 6)
        _r(s, (240, 220, 180), 5, 8, 6, 3)

    def heart(s):
        for x, y in ((4, 4), (8, 4)):
            pygame.draw.circle(s, (255, 90, 110), (x, y + 1), 2)
        pygame.draw.polygon(s, (255, 90, 110), [(2, 6), (11, 6), (7, 11)])

    def shotgun(s):
        _r(s, (230, 230, 240), 2, 5, 10, 2)
        _r(s, (230, 230, 240), 2, 8, 10, 2)

    def rifle(s):
        _r(s, (230, 230, 240), 1, 6, 12, 2)
        _r(s, (200, 140, 80), 1, 8, 4, 2)

    def bomb(s):
        pygame.draw.circle(s, (40, 40, 50), (7, 8), 4)
        _r(s, (250, 220, 120), 8, 2, 1, 3)
        s.set_at((9, 1), (255, 120, 40))

    def cash(s):
        pygame.draw.circle(s, (110, 220, 110), (7, 7), 4)
        _r(s, (30, 90, 40), 6, 4, 2, 6)

    return {"boots": _badge(boots), "heart": _badge(heart), "shotgun": _badge(shotgun),
            "rifle": _badge(rifle), "bomb": _badge(bomb), "cash": _badge(cash)}


def make_barrel():
    s = _surf(14, 14)
    pygame.draw.ellipse(s, (150, 96, 54), (0, 0, 14, 14))
    pygame.draw.ellipse(s, (180, 122, 72), (2, 2, 10, 10))
    pygame.draw.ellipse(s, (120, 74, 40), (4, 4, 6, 6))
    _r(s, (80, 60, 50), 0, 6, 14, 2)
    return outline(s)


def make_dynamite():
    s = _surf(6, 12)
    _r(s, (214, 50, 44), 1, 3, 4, 9)
    _r(s, (250, 230, 200), 1, 6, 4, 1)
    _r(s, (80, 70, 60), 3, 0, 1, 3)
    s.set_at((3, 0), (255, 200, 60))
    return outline(s)


class Sprites:
    """All sprite frames, built once at start-up."""

    def __init__(self):
        self.hero = {}
        self.portrait = {}
        for key in ("hank", "carl"):
            self.hero[key] = {(aim, step): humanoid(PALETTES[key], back=True, step=step, aim=aim)
                              for aim in (-2, 0, 2) for step in (0, 1)}
            front = humanoid(PALETTES[key], back=False)
            self.portrait[key] = pygame.transform.scale(front, (front.get_width() * 4, front.get_height() * 4))
        self.enemy = {k: [humanoid(PALETTES[k], step=0), humanoid(PALETTES[k], step=1)]
                      for k in ("outlaw", "gunman", "dynamite")}
        self.rider = [make_rider(0), make_rider(1)]
        self.boss = {k: [make_boss(k, 2, 0), make_boss(k, 2, 1)]
                     for k in ("jack", "lola", "mike", "cobra", "diablo")}
        self.items = make_items()
        self.barrel = make_barrel()
        self.dynamite = make_dynamite()
        self.heart_full = self._heart((240, 70, 90))
        self.heart_empty = self._heart((70, 40, 60))
        self.flash_cache = {}

    @staticmethod
    def _heart(color):
        s = _surf(11, 10)
        for x in (3, 7):
            pygame.draw.circle(s, color, (x, 3), 3)
        pygame.draw.polygon(s, color, [(0, 4), (10, 4), (5, 9)])
        return outline(s)

    def flashed(self, img):
        f = self.flash_cache.get(id(img))
        if f is None:
            f = self.flash_cache[id(img)] = flash(img)
        return f


# ----------------------------------------------------------------------------
# Stage backdrops
# ----------------------------------------------------------------------------
def _speckle(s, rng, rect, colors, n):
    x0, y0, w, h = rect
    for _ in range(n):
        c = rng.choice(colors)
        pygame.draw.rect(s, c, (x0 + rng.randint(0, w - 1), y0 + rng.randint(0, h - 1), rng.choice((1, 2, 2, 3)), 1))


def _building(rng, w, h, wall, sign):
    s = pygame.Surface((w, h))
    s.fill(wall)
    for y in range(0, h, 6):
        pygame.draw.line(s, shade(wall, 0.82), (0, y), (w, y))
    _r(s, shade(wall, 0.55), 0, 0, w, 10)
    _r(s, shade(wall, 0.75), 0, 10, w, 3)
    for x in range(4, w - 14, 22):
        _r(s, (40, 36, 52), x, 24, 14, 18)
        _r(s, (130, 190, 230), x + 2, 26, 10, 14)
        _r(s, (240, 240, 250), x + 2, 26, 4, 5)
        _r(s, shade(wall, 0.5), x - 1, 23, 16, 1)
    _r(s, (84, 52, 34), w // 2 - 6, h - 28, 12, 28)
    _r(s, (250, 220, 120), w // 2 + 3, h - 14, 2, 2)
    stripe = rng.choice(((200, 60, 60), (60, 120, 200), (60, 150, 80)))
    for x in range(0, w, 8):
        _r(s, stripe if (x // 8) % 2 == 0 else (240, 236, 220), x, 44, 8, 8)
    _r(s, shade(stripe, 0.6), 0, 52, w, 2)
    _r(s, (60, 40, 30), 4, 12, w - 8, 10)
    text(s, sign, 14, (w // 2, 17), (250, 226, 150), shadow=False)
    pygame.draw.rect(s, OUT, (0, 0, w, h), 1)
    return s


def _cactus(rng):
    s = _surf(14, 22)
    g, d = (70, 150, 80), (44, 110, 62)
    _r(s, g, 5, 2, 4, 20)
    _r(s, g, 1, 8, 3, 8)
    _r(s, g, 1, 14, 5, 2)
    _r(s, g, 10, 5, 3, 7)
    _r(s, g, 8, 11, 5, 2)
    _r(s, d, 7, 2, 2, 20)
    for y in range(4, 20, 4):
        s.set_at((6, y), (250, 240, 200))
    return outline(s)


def _crate():
    s = pygame.Surface((16, 16))
    s.fill((170, 120, 70))
    pygame.draw.rect(s, (110, 74, 44), (0, 0, 16, 16), 2)
    pygame.draw.line(s, (110, 74, 44), (0, 0), (15, 15), 2)
    pygame.draw.line(s, (110, 74, 44), (15, 0), (0, 15), 2)
    return s


def _boulder(rng, r):
    s = _surf(r * 2 + 2, r * 2 + 2)
    pygame.draw.circle(s, (126, 110, 100), (r + 1, r + 1), r)
    pygame.draw.circle(s, (160, 144, 130), (r - 1, r - 1), max(2, r - 4))
    pygame.draw.circle(s, (96, 82, 76), (r + 3, r + 3), max(2, r // 2))
    return outline(s)


class Stage:
    """A pre-rendered scrolling backdrop plus the solid obstacles and barrel positions on it."""

    def __init__(self, theme, length, seed):
        self.theme = theme
        self.length = length
        self.height = length + PLAY_H
        self.rng = random.Random(seed)
        self.surf = pygame.Surface((W, self.height))
        self.obstacles = []              # pygame.Rects in world coordinates
        self.barrels = []                # (x, wy)
        [self._town, self._canyon, self._rail, self._mine, self._hacienda][theme]()

    # ---- shared helpers
    def _block(self, img, x, y, rect=None):
        self.surf.blit(img, (x, y))
        self.obstacles.append(rect or pygame.Rect(x, y, img.get_width(), img.get_height()))

    def _free_x(self, y, lo, hi, w, gap=64):
        """Pick x in [lo,hi-w] that doesn't box in an obstacle placed in the last few rows."""
        for _ in range(12):
            x = self.rng.randint(lo, hi - w)
            near = [o for o in self.obstacles if abs(o.centery - y) < 40 and o.width < 120]
            if all(abs((x + w / 2) - o.centerx) > gap for o in near):
                return x
        return None

    def _scatter(self, lo, hi, imgs, every, jitter, y_from=PLAY_H + 40, y_to=None, barrel_chance=0.35):
        rng = self.rng
        y_to = y_to if y_to is not None else self.height - PLAY_H - 30
        y = y_from
        while y < y_to:
            y += every + rng.randint(-jitter, jitter)
            if y >= y_to:
                break
            kind = rng.random()
            if kind < barrel_chance:
                bx = rng.randint(lo + 10, hi - 24)
                self.barrels.append((bx, y))
                continue
            img = rng.choice(imgs)
            x = self._free_x(y, lo, hi, img.get_width())
            if x is not None:
                self._block(img, x, y)

    # ---- 0: Dusty Town
    def _town(self):
        rng, s = self.rng, self.surf
        s.fill((198, 152, 100))
        _speckle(s, rng, (0, 0, W, self.height), [(180, 136, 88), (214, 170, 118), (170, 126, 80)], self.height * 5)
        _r(s, (208, 164, 112), 62, 0, 196, self.height)
        for x in (112, 200):
            for y in range(0, self.height, 6):
                _r(s, (176, 132, 86), x + int(2 * math.sin(y * 0.03 + x)), y, 2, 4)
        signs = ["SALOON", "BANK", "HOTEL", "SHERIFF", "STORE", "SMITH", "BAR", "JAIL"]
        for side in (0, 1):
            y = -20
            while y < self.height:
                h = rng.randint(92, 118)
                w = 56
                img = _building(rng, w, h, rng.choice(((160, 110, 70), (176, 132, 84), (140, 96, 66), (190, 150, 100))),
                                rng.choice(signs))
                x = 0 if side == 0 else W - w
                s.blit(img, (x, y))
                self.obstacles.append(pygame.Rect(x, y, w, h))
                y += h + rng.randint(4, 22)
        cacti = [_cactus(rng) for _ in range(2)]
        crates = [_crate(), _crate()]
        self._scatter(64, W - 64, cacti + crates, 60, 18)
        for _ in range(int(self.height / 90)):
            x, y = rng.randint(70, W - 80), rng.randint(40, self.height - 40)
            pygame.draw.circle(s, (150, 110, 70), (x, y), 4, 1)           # tumbleweed

    # ---- 1: Canyon Pass
    def _canyon(self):
        rng, s = self.rng, self.surf
        s.fill((178, 106, 66))
        _speckle(s, rng, (0, 0, W, self.height), [(160, 92, 58), (196, 124, 80), (150, 84, 54)], self.height * 6)
        for y in range(0, self.height, 4):
            x = 150 + int(46 * math.sin(y * 0.011) + 20 * math.sin(y * 0.027))
            _r(s, (200, 150, 100), x - 26, y, 52, 4)
        edges = []
        e_l = e_r = 44.0
        for y in range(0, self.height, 8):
            e_l = max(24, min(78, e_l + rng.uniform(-6, 6)))
            e_r = max(24, min(78, e_r + rng.uniform(-6, 6)))
            edges.append((y, int(e_l), int(e_r)))
        for y, el, er in edges:
            for x0, x1, tone in ((0, el, 0), (W - er, W, 1)):
                _r(s, (112, 62, 46), x0, y, x1 - x0, 8)
                _r(s, (150, 88, 60), x1 - 4 if tone == 0 else x0, y, 4, 8)
                _r(s, (84, 44, 38), x0 if tone == 0 else x1 - 6, y, 6, 8)
        for i in range(0, len(edges), 4):
            y = edges[i][0]
            el = max(e[1] for e in edges[i:i + 4])
            er = max(e[2] for e in edges[i:i + 4])
            self.obstacles.append(pygame.Rect(0, y, el, 32))
            self.obstacles.append(pygame.Rect(W - er, y, er, 32))
        rocks = [_boulder(rng, r) for r in (8, 10, 12)]
        self._scatter(80, W - 80, rocks + [_cactus(rng)], 62, 18)

    # ---- 2: Rail Yard
    def _rail(self):
        rng, s = self.rng, self.surf
        s.fill((126, 116, 104))
        _speckle(s, rng, (0, 0, W, self.height), [(110, 100, 90), (146, 136, 122), (96, 88, 80)], self.height * 6)
        for cx in (118, 202):
            for y in range(0, self.height, 9):
                _r(s, (96, 66, 44), cx - 14, y, 28, 4)
            _r(s, (170, 176, 190), cx - 9, 0, 3, self.height)
            _r(s, (170, 176, 190), cx + 6, 0, 3, self.height)
            _r(s, (96, 100, 112), cx - 7, 0, 1, self.height)
        for side in (0, 1):
            y = 30
            while y < self.height - 60:
                h = rng.randint(96, 128)
                col = rng.choice(((150, 60, 52), (110, 80, 50), (60, 110, 80), (90, 90, 110)))
                car = pygame.Surface((46, h))
                car.fill(col)
                for yy in range(0, h, 7):
                    pygame.draw.line(car, shade(col, 0.8), (0, yy), (46, yy))
                _r(car, shade(col, 0.55), 0, 0, 46, 5)
                _r(car, shade(col, 0.55), 0, h - 5, 46, 5)
                _r(car, shade(col, 1.25), 4, 12, 38, 4)
                pygame.draw.rect(car, OUT, (0, 0, 46, h), 1)
                x = 0 if side == 0 else W - 46
                s.blit(car, (x, y))
                self.obstacles.append(pygame.Rect(x, y, 46, h))
                y += h + rng.randint(10, 40)
        self._scatter(50, W - 50, [_crate(), _crate(), _boulder(rng, 8)], 64, 16, barrel_chance=0.4)

    # ---- 3: Silver Mine
    def _mine(self):
        rng, s = self.rng, self.surf
        s.fill((72, 54, 48))
        _speckle(s, rng, (0, 0, W, self.height), [(58, 42, 40), (88, 68, 60), (46, 34, 34)], self.height * 7)
        for y in range(0, self.height, 8):
            _r(s, (104, 84, 70), 154, y, 12, 3)
        _r(s, (140, 142, 156), 156, 0, 2, self.height)
        _r(s, (140, 142, 156), 162, 0, 2, self.height)
        e_l = e_r = 40.0
        for y in range(0, self.height, 16):
            e_l = max(20, min(64, e_l + rng.uniform(-9, 9)))
            e_r = max(20, min(64, e_r + rng.uniform(-9, 9)))
            _r(s, (40, 30, 34), 0, y, int(e_l), 16)
            _r(s, (40, 30, 34), W - int(e_r), y, int(e_r), 16)
            _r(s, (64, 50, 54), int(e_l) - 3, y, 3, 16)
            _r(s, (64, 50, 54), W - int(e_r), y, 3, 16)
            self.obstacles.append(pygame.Rect(0, y, int(e_l), 16))
            self.obstacles.append(pygame.Rect(W - int(e_r), y, int(e_r), 16))
        for y in range(120, self.height - 120, 190):
            _r(s, (120, 80, 46), 60, y, 200, 8)
            _r(s, (84, 54, 32), 60, y + 8, 200, 2)
            for x in (60, 250):
                _r(s, (120, 80, 46), x, y - 2, 10, 14)
                self.obstacles.append(pygame.Rect(x, y - 2, 10, 14))
                glow = _surf(40, 40)
                pygame.draw.circle(glow, (255, 200, 90, 40), (20, 20), 20)
                pygame.draw.circle(glow, (255, 220, 120, 60), (20, 20), 9)
                s.blit(glow, (x - 15, y - 14))
                _r(s, (255, 230, 150), x + 3, y + 3, 4, 4)
        cart = pygame.Surface((28, 22))
        cart.fill((100, 100, 112))
        pygame.draw.rect(cart, (60, 60, 72), (0, 0, 28, 22), 2)
        pygame.draw.ellipse(cart, (180, 190, 210), (4, 4, 20, 14))
        self._scatter(70, W - 70, [cart, _boulder(rng, 9), _crate()], 64, 16)

    # ---- 4: Hacienda
    def _hacienda(self):
        rng, s = self.rng, self.surf
        for ty in range(0, self.height, 16):
            for tx in range(0, W, 16):
                c = (214, 184, 142) if (tx // 16 + ty // 16) % 2 == 0 else (202, 170, 130)
                _r(s, c, tx, ty, 16, 16)
        _speckle(s, rng, (0, 0, W, self.height), [(190, 158, 120), (224, 196, 156)], self.height * 2)
        for y in range(0, self.height, 8):
            _r(s, (150, 30, 40), 138, y, 44, 8)
            _r(s, (210, 170, 70), 138, y, 2, 8)
            _r(s, (210, 170, 70), 180, y, 2, 8)
        for side in (0, 1):
            x0 = 0 if side == 0 else W - 40
            _r(s, (222, 190, 150), x0, 0, 40, self.height)
            for y in range(6, self.height, 44):
                _r(s, (96, 60, 44), x0 + 8, y, 24, 30)
                pygame.draw.ellipse(s, (96, 60, 44), (x0 + 8, y - 8, 24, 16))
                _r(s, (150, 190, 220), x0 + 12, y + 4, 16, 22)
                _r(s, (182, 140, 100), x0 + (36 if side == 0 else 0), 0, 4, self.height)
            self.obstacles.append(pygame.Rect(x0, 0, 40, self.height))
        fountain = _surf(40, 40)
        pygame.draw.circle(fountain, (150, 140, 130), (20, 20), 19)
        pygame.draw.circle(fountain, (90, 170, 220), (20, 20), 15)
        pygame.draw.circle(fountain, (200, 230, 250), (20, 20), 6)
        fountain = outline(fountain)
        for y in range(140, self.height - 140, 230):
            x = rng.choice((60, 220))
            self._block(fountain, x, y, pygame.Rect(x + 4, y + 4, 34, 34))
        pot = _cactus(rng)
        self._scatter(48, W - 48, [pot, _crate(), pot], 64, 16)
