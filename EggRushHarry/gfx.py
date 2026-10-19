"""Procedural pixel-art graphics: sprites, level backdrops and text.

Everything is drawn in code at the logical 320x256 resolution, so the game
ships without any image files.
"""
import math
import random

import pygame

from config import (W, H, OY, TILE, COLS, FLOOR_ROWS, GROUND_ROW, THEMES, CAGE_RECT, MOMMA_SCALE)

OUT = (24, 16, 30)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _rect(s, c, x, y, w, h):
    pygame.draw.rect(s, c, (x, y, w, h))


def outline(s, color=OUT):
    """Add a 1px dark outline around the opaque pixels of a sprite."""
    w, h = s.get_size()
    out = _surf(w + 2, h + 2)
    sil = pygame.mask.from_surface(s, 40).to_surface(setcolor=color + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, (dx, dy))
    out.blit(s, (1, 1))
    return out


_fonts = {}


def text(surf, s, size, pos, color=(255, 255, 255), anchor="center", shadow=True):
    f = _fonts.get(size)
    if f is None:
        f = _fonts[size] = pygame.font.Font(None, size)
    img = f.render(s, False, color)
    r = img.get_rect()
    setattr(r, anchor, pos)
    if shadow:
        sh = f.render(s, False, (20, 12, 28))
        surf.blit(sh, r.move(1, 1))
    surf.blit(img, r)
    return r


# ----------------------------------------------------------------------------
# Harry
# ----------------------------------------------------------------------------
SKIN, SKIN_D = (250, 205, 165), (214, 152, 112)
HAT, HAT_D = (246, 206, 64), (196, 140, 32)
HAIR = (120, 72, 36)
SHIRT, SHIRT_D = (246, 246, 240), (186, 198, 220)
OVER, OVER_D = (214, 56, 56), (150, 34, 46)
BOOT, BOOT_D = (116, 70, 38), (72, 42, 24)


def _harry(legs, arms, back=False):
    s = _surf(14, 22)
    for lx, ly, lh in legs:
        _rect(s, OVER_D, lx, ly, 3, lh)
        _rect(s, BOOT, lx, ly + lh, 4, 2)
        _rect(s, BOOT_D, lx, ly + lh + 1, 4, 1)
    for ax, ay, ah in arms:
        _rect(s, SHIRT, ax, ay, 2, ah)
        _rect(s, SKIN, ax, ay + ah, 2, 2)
    _rect(s, SHIRT, 3, 10, 8, 4)
    _rect(s, SHIRT_D, 3, 13, 8, 1)
    _rect(s, OVER, 3, 13, 8, 4)
    _rect(s, OVER_D, 3, 16, 8, 1)
    if not back:
        _rect(s, OVER, 5, 10, 4, 3)
        _rect(s, (255, 226, 96), 5, 12, 1, 1)
        _rect(s, (255, 226, 96), 8, 12, 1, 1)
    _rect(s, SKIN, 4, 5, 6, 5)
    if back:
        _rect(s, HAIR, 4, 5, 6, 5)
    else:
        _rect(s, HAIR, 4, 5, 1, 3)
        _rect(s, SKIN_D, 9, 8, 1, 1)
        _rect(s, (30, 20, 30), 8, 6, 1, 2)
        _rect(s, (255, 255, 255), 7, 6, 1, 1)
    _rect(s, HAT, 4, 0, 6, 3)
    _rect(s, (200, 60, 50), 4, 2, 6, 1)
    _rect(s, HAT, 2, 3, 10, 2)
    _rect(s, HAT_D, 2, 4, 10, 1)
    return outline(s)


def make_harry():
    idle = [(4, 17, 3), (7, 17, 3)]
    arm0 = [(2, 10, 3), (10, 10, 3)]
    f = {
        "idle": _harry(idle, arm0),
        "walk0": _harry([(3, 17, 3), (8, 16, 3)], [(2, 10, 2), (10, 11, 3)]),
        "walk1": _harry([(4, 16, 3), (9, 17, 3)], [(2, 11, 3), (10, 10, 2)]),
        "jump": _harry([(3, 16, 2), (8, 16, 2)], [(2, 6, 3), (10, 6, 3)]),
        "climb0": _harry([(4, 17, 3), (7, 15, 3)], [(2, 6, 3), (10, 11, 3)], back=True),
        "climb1": _harry([(4, 15, 3), (7, 17, 3)], [(2, 11, 3), (10, 6, 3)], back=True),
    }
    return f


# ----------------------------------------------------------------------------
# Hen
# ----------------------------------------------------------------------------
def _hen(step, eat=False):
    s = _surf(19, 16)
    leg = (232, 150, 40)
    offs = ((0, 0), (0, 0)) if step == 0 else (((-1, 0), (1, -1)) if step == 1 else ((1, -1), (-1, 0)))
    for lx, (dx, dy) in zip((6, 10), offs):
        _rect(s, leg, lx + dx, 12 + dy, 1, 3 - dy)
        _rect(s, leg, lx + dx - 1, 15 + dy, 3, 1)
    pygame.draw.polygon(s, (150, 98, 66), [(0, 2), (4, 4), (4, 9), (1, 8)])
    pygame.draw.polygon(s, (190, 130, 90), [(0, 2), (3, 3), (3, 6), (1, 5)])
    pygame.draw.ellipse(s, (242, 234, 212), (2, 4, 12, 9))
    pygame.draw.ellipse(s, (214, 198, 166), (3, 9, 10, 4))
    pygame.draw.ellipse(s, (206, 168, 122), (4, 6, 6, 5))
    pygame.draw.ellipse(s, (170, 130, 90), (5, 8, 4, 2))
    if eat:
        _rect(s, (242, 234, 212), 11, 7, 3, 4)
        pygame.draw.ellipse(s, (242, 234, 212), (12, 9, 5, 5))
        pygame.draw.polygon(s, (250, 190, 40), [(16, 11), (18, 13), (15, 13)])
        _rect(s, (210, 40, 50), 13, 7, 3, 2)
        _rect(s, (20, 14, 20), 14, 10, 1, 1)
    else:
        _rect(s, (242, 234, 212), 11, 4, 3, 5)
        pygame.draw.ellipse(s, (242, 234, 212), (11, 1, 5, 6))
        pygame.draw.polygon(s, (250, 190, 40), [(16, 3), (19, 4), (16, 6)])
        _rect(s, (210, 40, 50), 12, 0, 3, 2)
        _rect(s, (210, 40, 50), 16, 6, 1, 2)
        _rect(s, (20, 14, 20), 14, 3, 1, 1)
    return outline(s)


def make_hen():
    return {"w0": _hen(1), "w1": _hen(2), "idle": _hen(0), "eat": _hen(0, True)}


# ----------------------------------------------------------------------------
# Egg and grain
# ----------------------------------------------------------------------------
def make_egg(glint=False):
    s = _surf(8, 10)
    pygame.draw.ellipse(s, (240, 230, 200), (0, 0, 8, 10))
    pygame.draw.ellipse(s, (252, 248, 236), (0, 0, 6, 8))
    _rect(s, (206, 192, 160), 6, 4, 1, 4)
    _rect(s, (255, 255, 255), 2, 1, 2, 2)
    if glint:
        _rect(s, (255, 255, 160), 5, 2, 1, 1)
    return outline(s)


def make_grain():
    s = _surf(14, 8)
    pygame.draw.polygon(s, (222, 172, 52), [(0, 7), (4, 3), (7, 0), (10, 3), (13, 7)])
    pygame.draw.polygon(s, (252, 214, 100), [(2, 6), (5, 3), (7, 1), (7, 6)])
    for x, y in ((3, 5), (6, 4), (9, 5), (8, 3), (5, 6), (11, 6)):
        s.set_at((x, y), (170, 118, 30))
    for x, y in ((4, 4), (7, 2), (7, 5)):
        s.set_at((x, y), (255, 238, 150))
    return outline(s)


# ----------------------------------------------------------------------------
# The big bird and its cage
# ----------------------------------------------------------------------------
def _bird(flap):
    s = _surf(40, 32)
    body, body_hi, belly = (64, 52, 104), (92, 78, 140), (150, 134, 190)
    wing, wing_d = (84, 68, 130), (56, 44, 92)
    if flap == 0:      # wings up
        pygame.draw.polygon(s, wing_d, [(8, 16), (12, 0), (26, 13)])
        pygame.draw.polygon(s, wing, [(10, 15), (14, 3), (22, 13)])
    pygame.draw.polygon(s, body, [(4, 16), (0, 9), (9, 13)])
    pygame.draw.polygon(s, body_hi, [(4, 16), (2, 12), (8, 14)])
    pygame.draw.ellipse(s, body, (3, 12, 27, 16))
    pygame.draw.ellipse(s, belly, (8, 19, 17, 8))
    pygame.draw.ellipse(s, body_hi, (8, 13, 14, 5))
    if flap == 1:      # wings down
        pygame.draw.polygon(s, wing_d, [(8, 20), (6, 31), (24, 24)])
        pygame.draw.polygon(s, wing, [(10, 20), (10, 29), (21, 23)])
    pygame.draw.ellipse(s, body, (22, 3, 14, 13))
    pygame.draw.ellipse(s, body_hi, (23, 4, 8, 5))
    pygame.draw.polygon(s, (252, 190, 40), [(35, 8), (40, 11), (35, 14)])
    pygame.draw.polygon(s, (214, 140, 24), [(35, 11), (40, 11), (35, 14)])
    _rect(s, (255, 255, 255), 30, 6, 4, 4)
    _rect(s, (210, 30, 40), 32, 7, 2, 3)
    _rect(s, (24, 16, 30), 29, 4, 6, 1)          # angry brow
    _rect(s, (24, 16, 30), 31, 5, 3, 1)
    _rect(s, (252, 190, 40), 14, 27, 1, 3)
    _rect(s, (252, 190, 40), 20, 27, 1, 3)
    return outline(s)


def make_bird():
    return {0: _bird(0), 1: _bird(1)}


def make_cage(open_door):
    w, h = CAGE_RECT[2], CAGE_RECT[3]
    s = _surf(w, h)
    bar, bar_hi = (96, 100, 120), (170, 176, 200)
    _rect(s, bar, 0, 0, w, 3)
    _rect(s, bar_hi, 0, 0, w, 1)
    for x in range(2, w - 2, 6):
        if open_door and 18 <= x <= 38:
            continue
        _rect(s, bar, x, 3, 2, h - 6)
        _rect(s, bar_hi, x, 3, 1, h - 6)
    if open_door:
        pygame.draw.line(s, bar, (20, 4), (31, 14), 2)
        pygame.draw.line(s, bar, (36, 4), (45, 10), 2)
    _rect(s, bar, 0, h - 4, w, 4)
    _rect(s, (60, 64, 80), 0, h - 2, w, 2)
    return outline(s)


# ----------------------------------------------------------------------------
# Level backdrop
# ----------------------------------------------------------------------------
def _plank(theme, tone):
    base = shade(theme["plank"], tone)
    s = _surf(TILE, 8)
    _rect(s, base, 0, 0, TILE, 8)
    _rect(s, shade(base, 1.35), 0, 0, TILE, 2)
    _rect(s, shade(base, 1.15), 0, 2, TILE, 1)
    _rect(s, shade(base, 0.7), 0, 6, TILE, 2)
    _rect(s, shade(base, 0.8), 0, 3, 1, 3)
    for x in (3, 12):
        _rect(s, shade(base, 0.55), x, 4, 1, 1)
    return s


def _ground_tile(theme, seed):
    rng = random.Random(seed)
    s = _surf(TILE, TILE)
    soil = (96, 62, 44)
    _rect(s, soil, 0, 0, TILE, TILE)
    for _ in range(14):
        _rect(s, shade(soil, rng.choice((0.8, 1.2))), rng.randint(0, 14), rng.randint(4, 14), 2, 1)
    g = theme["grass"]
    _rect(s, g, 0, 0, TILE, 4)
    _rect(s, shade(g, 1.3), 0, 0, TILE, 1)
    _rect(s, shade(g, 0.7), 0, 4, TILE, 1)
    for x in range(0, TILE, 2):
        if rng.random() < 0.6:
            _rect(s, shade(g, 1.2), x, 0, 1, 1)
        if rng.random() < 0.5:
            _rect(s, shade(g, 0.75), x, 4 + rng.randint(0, 1), 1, 1)
    return s


def _ladder_tile():
    s = _surf(TILE, TILE)
    rail, rail_hi, rung = (190, 138, 82), (230, 184, 120), (140, 96, 56)
    for x in (3, 11):
        _rect(s, rail, x, 0, 2, TILE)
        _rect(s, rail_hi, x, 0, 1, TILE)
        _rect(s, shade(rail, 0.6), x + 1, 0, 1, TILE)
    for y in (2, 7, 12):
        _rect(s, rung, 3, y, 10, 2)
        _rect(s, shade(rung, 1.35), 3, y, 10, 1)
    return s


def make_lift():
    w = 2 * TILE
    s = _surf(w, 8)
    _rect(s, (96, 100, 120), 0, 0, w, 8)
    _rect(s, (170, 176, 200), 0, 0, w, 2)
    for x in range(0, w, 8):
        _rect(s, (246, 206, 64), x, 3, 4, 3)
        _rect(s, (36, 30, 44), x + 4, 3, 4, 3)
    _rect(s, (50, 52, 70), 0, 7, w, 1)
    return s


def render_level(level):
    """Pre-render the sky, scenery, platforms and ladders for a level."""
    theme = THEMES[level.k]
    rng = random.Random(900 + level.k)
    surf = pygame.Surface((W, H))
    top, bot = theme["sky"]
    for y in range(H):
        t = max(0.0, (y - OY) / (H - OY))
        pygame.draw.line(surf, lerp(top, bot, t ** 1.2), (0, y), (W, y))
    if theme["stars"]:
        for _ in range(70):
            x, y = rng.randint(0, W - 1), rng.randint(OY, OY + 150)
            c = rng.choice(((255, 255, 255), (200, 210, 255), (255, 235, 190)))
            surf.set_at((x, y), c)
            if rng.random() < 0.15:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    surf.set_at((x + dx, y + dy), shade(c, 0.5))
    ox, oy = theme["orb_pos"]
    for r, f in ((16, 0.25), (13, 0.5)):
        glow = _surf(2 * r + 2, 2 * r + 2)
        pygame.draw.circle(glow, theme["orb"] + (int(255 * f * 0.35),), (r + 1, r + 1), r)
        surf.blit(glow, (ox - r - 1, oy - r - 1))
    pygame.draw.circle(surf, theme["orb"], (ox, oy), 9)
    pygame.draw.circle(surf, shade(theme["orb"], 0.85), (ox + 3, oy + 2), 3)
    far, near = theme["hill"]
    for col, base, amp, freq, ph in ((far, 196, 14, 0.021, 1.0), (near, 214, 10, 0.034, 3.0)):
        pts = [(0, H)] + [(x, base + amp * math.sin(x * freq + ph)) for x in range(0, W + 8, 8)] + [(W, H)]
        pygame.draw.polygon(surf, col, pts)
    # barn, silo and trees
    dark = shade(near, 0.7)
    bx, by = 236, GROUND_ROW * TILE + OY
    pygame.draw.rect(surf, dark, (bx, by - 30, 44, 30))
    pygame.draw.polygon(surf, shade(dark, 0.85), [(bx - 4, by - 30), (bx + 22, by - 52), (bx + 48, by - 30)])
    pygame.draw.rect(surf, shade(dark, 1.4), (bx + 16, by - 18, 12, 18))
    pygame.draw.line(surf, dark, (bx + 16, by - 18), (bx + 28, by), 1)
    pygame.draw.rect(surf, (250, 210, 110), (bx + 6, by - 24, 5, 5))
    pygame.draw.rect(surf, dark, (bx + 50, by - 42, 14, 42))
    pygame.draw.ellipse(surf, dark, (bx + 50, by - 50, 14, 16))
    for tx in (22, 120, 176):
        pygame.draw.rect(surf, dark, (tx - 2, by - 14, 4, 14))
        pygame.draw.circle(surf, shade(dark, 1.1), (tx, by - 22), 11)
        pygame.draw.circle(surf, shade(dark, 0.9), (tx + 5, by - 17), 8)
    # platforms
    planks = [_plank(theme, t) for t in (0.94, 1.0, 1.06)]
    ground = [_ground_tile(theme, s) for s in range(4)]
    for (r, c) in sorted(level.floors):
        if (r, c) in level.ladders:
            continue
        x, y = c * TILE, OY + r * TILE
        if r == GROUND_ROW:
            surf.blit(ground[(c * 7) % 4], (x, y))
        else:
            surf.blit(planks[(c + r) % 3], (x, y))
    for c0, c1 in level.shafts:       # lift shafts: dark well with a rail down each side
        top, bot = OY + FLOOR_ROWS[0] * TILE, H
        well = _surf((c1 - c0 + 1) * TILE, bot - top)
        well.fill((10, 8, 20, 90))
        surf.blit(well, (c0 * TILE, top))
        for x in (c0 * TILE, (c1 + 1) * TILE - 2):
            _rect(surf, (96, 100, 120), x, top, 2, bot - top)
            _rect(surf, (170, 176, 200), x, top, 1, bot - top)
    lad = _ladder_tile()
    for (r, c) in level.ladders:
        surf.blit(lad, (c * TILE, OY + r * TILE))
    # soft shadow under each plank
    for (r, c) in level.floors:
        if r != GROUND_ROW and (r, c) not in level.ladders:
            sh = _surf(TILE, 3)
            sh.fill((0, 0, 0, 60))
            surf.blit(sh, (c * TILE, OY + r * TILE + 8))
    return surf


class Sprites:
    """All sprite frames, built once at start-up."""

    def __init__(self):
        self.harry = make_harry()
        self.hen = make_hen()
        self.egg = [make_egg(False), make_egg(True)]
        self.grain = make_grain()
        self.lift = make_lift()
        self.bird = make_bird()
        self.cage_shut = make_cage(False)
        self.cage_open = make_cage(True)
        small = pygame.transform.scale(self.bird[1], (30, 24))
        self.bird_small = small
        self.momma = {}
        for name in ("w0", "w1"):
            img = self.hen[name]
            big = pygame.transform.scale(img, (img.get_width() * MOMMA_SCALE, img.get_height() * MOMMA_SCALE))
            angry = big.copy()
            angry.fill((90, 0, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
            self.momma[(name, False)] = big
            self.momma[(name, True)] = angry
