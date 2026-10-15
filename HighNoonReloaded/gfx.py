"""Procedural 16-bit style graphics: sprites, backgrounds, text and UI pieces.

Everything is drawn in code at the logical 400x225 resolution, so the game
ships without any image files.
"""
import math
import random

import pygame

from config import W, H, HUD_H, HORIZON

BAYER = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)
OUTLINE = (22, 12, 10)
SRCALPHA = pygame.SRCALPHA


# ----------------------------------------------------------------------------
# Colour helpers
# ----------------------------------------------------------------------------
def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def dither_fill(surf, rect, c1, c2, steps=8):
    """Vertical gradient quantised into bands and blended with a Bayer dither."""
    rect = pygame.Rect(rect)
    h = rect.h
    for y in range(h):
        t = y / max(1, h - 1) * (steps - 1)
        i = int(t)
        f = t - i
        ca = lerp(c1, c2, i / (steps - 1))
        cb = lerp(c1, c2, min(steps - 1, i + 1) / (steps - 1))
        yy = rect.y + y
        pygame.draw.line(surf, ca, (rect.x, yy), (rect.right - 1, yy))
        thr = f * 16
        if thr > 0.5:
            row = BAYER[yy % 4]
            for x in range(rect.x, rect.right):
                if row[x % 4] < thr:
                    surf.set_at((x, yy), cb)


# ----------------------------------------------------------------------------
# Text
# ----------------------------------------------------------------------------
_fonts = {}
_fancy = {}

# Hand-drawn 5x7 pixel font used for all small text (sizes <= 13).
_GLYPHS = {
    "A": ".###. #...# #...# ##### #...# #...# #...#", "B": "####. #...# #...# ####. #...# #...# ####.",
    "C": ".###. #...# #.... #.... #.... #...# .###.", "D": "####. #...# #...# #...# #...# #...# ####.",
    "E": "##### #.... #.... ####. #.... #.... #####", "F": "##### #.... #.... ####. #.... #.... #....",
    "G": ".###. #...# #.... #.### #...# #...# .####", "H": "#...# #...# #...# ##### #...# #...# #...#",
    "I": ".###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.", "J": "..### ...#. ...#. ...#. ...#. #..#. .##..",
    "K": "#...# #..#. #.#.. ##... #.#.. #..#. #...#", "L": "#.... #.... #.... #.... #.... #.... #####",
    "M": "#...# ##.## #.#.# #.#.# #...# #...# #...#", "N": "#...# #...# ##..# #.#.# #..## #...# #...#",
    "O": ".###. #...# #...# #...# #...# #...# .###.", "P": "####. #...# #...# ####. #.... #.... #....",
    "Q": ".###. #...# #...# #...# #.#.# #..#. .##.#", "R": "####. #...# #...# ####. #.#.. #..#. #...#",
    "S": ".#### #.... #.... .###. ....# ....# ####.", "T": "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..",
    "U": "#...# #...# #...# #...# #...# #...# .###.", "V": "#...# #...# #...# #...# #...# .#.#. ..#..",
    "W": "#...# #...# #...# #.#.# #.#.# #.#.# .#.#.", "X": "#...# #...# .#.#. ..#.. .#.#. #...# #...#",
    "Y": "#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..", "Z": "##### ....# ...#. ..#.. .#... #.... #####",
    "0": ".###. #...# #..## #.#.# ##..# #...# .###.", "1": "..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.",
    "2": ".###. #...# ....# ...#. ..#.. .#... #####", "3": "####. ....# ....# .###. ....# ....# ####.",
    "4": "...#. ..##. .#.#. #..#. ##### ...#. ...#.", "5": "##### #.... ####. ....# ....# #...# .###.",
    "6": ".###. #.... #.... ####. #...# #...# .###.", "7": "##### ....# ...#. ..#.. .#... .#... .#...",
    "8": ".###. #...# #...# .###. #...# #...# .###.", "9": ".###. #...# #...# .#### ....# ....# .###.",
    ".": "..... ..... ..... ..... ..... .##.. .##..", ",": "..... ..... ..... ..... .##.. ..#.. .#...",
    "!": "..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#..", "?": ".###. #...# ....# ...#. ..#.. ..... ..#..",
    "'": "..#.. ..#.. .#... ..... ..... ..... .....", '"': ".#.#. .#.#. ..... ..... ..... ..... .....",
    "-": "..... ..... ..... .###. ..... ..... .....", ":": "..... .##.. .##.. ..... .##.. .##.. .....",
    "/": "....# ....# ...#. ..#.. .#... #.... #....", "$": "..#.. .#### #.#.. .###. ..#.# ####. ..#..",
    "%": "##..# ##..# ...#. ..#.. .#... #..## #..##", "<": "...#. ..#.. .#... #.... .#... ..#.. ...#.",
    ">": ".#... ..#.. ...#. ....# ...#. ..#.. .#...", "(": "...#. ..#.. .#... .#... .#... ..#.. ...#.",
    ")": ".#... ..#.. ...#. ...#. ...#. ..#.. .#...", "+": "..... ..#.. ..#.. ##### ..#.. ..#.. .....",
    "=": "..... ..... ##### ..... ##### ..... .....",
}
_glyph_cache = {}
_bitmap_cache = {}


def _glyph(ch):
    g = _glyph_cache.get(ch)
    if g is None:
        rows = _GLYPHS.get(ch)
        if rows is None:
            g = ([], 3)                      # space / unknown
        else:
            rows = rows.split()
            cols = [x for x in range(5) if any(r[x] == "#" for r in rows)]
            lo, hi = cols[0], cols[-1]
            pix = [(x - lo, y) for y, r in enumerate(rows) for x in range(5) if r[x] == "#"]
            g = (pix, hi - lo + 1)
        _glyph_cache[ch] = g
    return g


def bitmap_text(s, color):
    key = (s, color)
    img = _bitmap_cache.get(key)
    if img is None:
        s = s.upper()
        glyphs = [_glyph(c) for c in s]
        w = max(1, sum(g[1] + 1 for g in glyphs) - 1)
        img = pygame.Surface((w, 7), SRCALPHA)
        x = 0
        for pix, gw in glyphs:
            for px, py in pix:
                img.set_at((x + px, py), color)
            x += gw + 1
        if len(_bitmap_cache) > 600:
            _bitmap_cache.clear()
        _bitmap_cache[key] = img
    return img


def font(size):
    f = _fonts.get(size)
    if f is None:
        f = pygame.font.Font(None, size)
        _fonts[size] = f
    return f


def _render(s, size, color, smooth=False):
    if smooth:
        return font(size).render(s, True, color)
    if size <= 13:
        return bitmap_text(s, color)
    return font(size).render(s, False, color)


def text_width(s, size):
    return _render(s, size, (0, 0, 0)).get_width()


def wrap(s, size, max_w):
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if cur and text_width(trial, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def text(surf, s, size, pos, color=(255, 236, 200), anchor="center", shadow=(28, 14, 8), outline=False,
         smooth=False):
    img = _render(s, size, color, smooth)
    r = img.get_rect(**{anchor: pos})
    if shadow is not None:
        sh = _render(s, size, shadow, smooth)
        if outline:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1)):
                surf.blit(sh, (r.x + dx, r.y + dy))
        else:
            surf.blit(sh, (r.x + 1, r.y + 1))
    surf.blit(img, r)
    return r


def fancy_text(s, size, top, bottom, outline=(30, 12, 6), thick=2):
    """Banded-gradient title text with a chunky outline and drop shadow."""
    key = (s, size, top, bottom, outline, thick)
    if key in _fancy:
        return _fancy[key]
    f = font(size)
    base = f.render(s, False, (255, 255, 255)).convert_alpha()
    w, h = base.get_size()
    grad = pygame.Surface((w, h), SRCALPHA)
    for y in range(h):
        t = round(y / max(1, h - 1) * 4) / 4
        pygame.draw.line(grad, lerp(top, bottom, t), (0, y), (w - 1, y))
    hi = lerp(top, (255, 255, 255), 0.6)
    pygame.draw.line(grad, hi, (0, h // 5), (w - 1, h // 5))
    grad.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    sil = f.render(s, False, outline).convert_alpha()
    out = pygame.Surface((w + thick * 2, h + thick * 2 + 2), SRCALPHA)
    for dx in range(-thick, thick + 1):
        for dy in range(-thick, thick + 3):
            out.blit(sil, (thick + dx, thick + dy))
    out.blit(grad, (thick, thick))
    _fancy[key] = out
    return out


# ----------------------------------------------------------------------------
# Sprite building
# ----------------------------------------------------------------------------
def from_rows(rows, colors):
    w = max(len(r) for r in rows)
    s = pygame.Surface((w, len(rows)), SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            c = colors.get(ch)
            if c:
                s.set_at((x, y), c)
    return s


def silhouette(surf, color):
    out = pygame.Surface(surf.get_size(), SRCALPHA)
    pygame.mask.from_surface(surf).to_surface(out, setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    return out


def outlined(surf, color=OUTLINE):
    w, h = surf.get_size()
    out = pygame.Surface((w + 2, h + 2), SRCALPHA)
    sil = silhouette(surf, color)
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, (dx, dy))
    out.blit(surf, (1, 1))
    return out


HEAD = [
    "......HHHH........",
    ".....HHHHHH.......",
    ".....HhhhhH.......",
    "..HHHHHHHHHHHH....",
    "...HHHHHHHHHH.....",
    "......SSSSs.......",
    "......SSSESs......",
    "......SSSSSS......",
    "......sMMMs.......",
    ".......NNN........",
]
T_IDLE = [
    ".....CVVCCVV......",
    "....CCVVCCVVC.....",
    "....CCVVCCVVC.....",
    "....SCVVCCVVS.....",
    "....SBBBBbBBG.....",
    ".....PPPPPPPG.....",
]
T_STRAIGHT = [
    ".....CVVCCVV......",
    "....CCVVCCCCCSGGG.",
    "....CCVVCCVV..gg..",
    "....SCVVCCVV......",
    "....SBBBBbBB......",
    ".....PPPPPPP......",
]
T_UP = [
    ".....CVVCCVVCSGG..",
    "....CCVVCCVCC.g...",
    "....CCVVCCVV......",
    "....SCVVCCVV......",
    "....SBBBBbBB......",
    ".....PPPPPPP......",
]
T_DOWN = [
    ".....CVVCCVV......",
    "....CCVVCCVVC.....",
    "....CCVVCCVVCC....",
    "....SCVVCCVV.CSGG.",
    "....SBBBBbBB...gG.",
    ".....PPPPPPP......",
]
L_IDLE = [
    ".....PPPpPPP......",
    ".....PPP.PPP......",
    ".....PPP.PPP......",
    ".....PPP.PPP......",
    ".....PPp.PPp......",
    ".....KKK.KKK......",
    "....KKKK.KKKK.....",
    "....KKKK.KKKK.....",
]
L_A = [
    ".....PPPpPPP......",
    "....PPP...PPP.....",
    "....PPP...PPP.....",
    "...PPP.....PPP....",
    "...PPp.....PPp....",
    "...KKK.....KKK....",
    "..KKKK.....KKKK...",
    "..KKKK.....KKKK...",
]
L_B = [
    ".....PPPpPPP......",
    "......PPPPP.......",
    "......PPPPP.......",
    "......PPPPp.......",
    "......PPpPp.......",
    "......KKKKK.......",
    ".....KKKKKKK......",
    ".....KKKKKK.......",
]

# --- "lady" body: the desperada (same frame geometry as the normal body) ---
F_HEAD = [
    "......HHHH........",
    ".....HHHHHH.......",
    ".....HhhhhH.......",
    "..HHHHHHHHHHHH....",
    "...HHHHHHHHHH.....",
    "....MMSSSSs.......",
    "....MMSSSES.......",
    "...MMMSSSSS.......",
    "...MMMsSLs........",
    "...MMM.NNN........",
]
F_T_IDLE = [
    "..MMMCCVVCC.......",
    "..MM.CCVVVCC......",
    "..M..CVVVVC.......",
    "....SCVVVVCS......",
    "....S.BBbBB.G.....",
    ".....PPPPPPPG.....",
]
F_T_STRAIGHT = [
    "..MMMCCVVCC.......",
    "..MM.CCVVVCCCSGGG.",
    "..M..CVVVVCCCSGGG.",
    ".....CVVVVC.......",
    ".....BBbBBB.......",
    ".....PPPPPPP......",
]
F_T_UP = [
    "..MMMCCVVCCCCSGG..",
    "..MM.CCVVVCCCSGG..",
    "..M..CVVVVC.......",
    ".....CVVVVC.......",
    ".....BBbBBB.......",
    ".....PPPPPPP......",
]
F_T_DOWN = [
    "..MMMCCVVCC.......",
    "..MM.CCVVVCC......",
    "..M..CVVVVCC......",
    ".....CVVVVC.CSGGG.",
    ".....BBbBB..CSGGG.",
    ".....PPPPPPP......",
]
F_L_IDLE = [
    ".....PPPPPPP......",
    ".....PPPPPPPP.....",
    "....PPPPPPPPP.....",
    "....PPPpPPPPP.....",
    "...PPPPpPPPPPP....",
    "...ppppppppppp....",
    ".....KKK.KKK......",
    "....KKKK.KKKK.....",
]
F_L_A = [
    ".....PPPPPPP......",
    "....PPPPPPPPP.....",
    "....PPPPPPPPPP....",
    "...PPPPpPPPPPP....",
    "..PPPPPpPPPPPPP...",
    "..ppppppppppppp...",
    "...KKK.....KKK....",
    "..KKKK.....KKKK...",
]
F_L_B = [
    ".....PPPPPPP......",
    ".....PPPPPPPP.....",
    ".....PPPPPPPP.....",
    "....PPPPpPPPP.....",
    "....PPPPpPPPPP....",
    "....pppppppppp....",
    "......KKKKK.......",
    ".....KKKKKK.......",
]

# --- "girl" body: hair with a ribbon instead of a hat, dress made of the lady rows ---
G_HEAD = [
    "..................",
    "......MMMM........",
    ".....MMMMMM.......",
    "....MMMMMMMM......",
    "....MMMhhMMM......",
    "....MMSSSSs.......",
    "....MMSSSES.......",
    "...MMMSSSSS.......",
    "...MMMsSLs........",
    "...MMM.NNN........",
]

# --- "brute" body: the muscle-bound final boss (bigger frame) ---
B_HEAD = [
    "........R.....R...........",
    "........RHHHHHR...........",
    ".........HHHHH............",
    ".........HhhhH............",
    ".....HHHHHHHHHHHHH........",
    "......HHHHHHHHHHH.........",
    ".........SSSSs............",
    ".........SSSESs...........",
    ".........SSSSSS...........",
    ".........MMMMMs...........",
    "........sSMMMSSs..........",
]
_B_LOW = [
    "..QSSs.VsssSsssV..........",
    "..SSs..VSQsSQsSV..........",
    "..QSS..VSsSsSsSV..........",
    "..SSs..VSQsSQsSV..........",
    "..sSS..BBBBbbBBB..........",
    ".sSSSs.PPPPPPPPP..........",
    "..sSs..PPPPPPPPP..........",
]
B_T_IDLE = [
    "....sQQSNNNNNSQQs.........",
    "..sQQS.VQQSsSQQV.SQQs.....",
    "..QQSS.VQSSsSSQV.SSQQ.....",
    "..QSSs.VsssSsssV.sSSQ.....",
    "..SSs..VSQsSQsSV..sSS.....",
    "..QSS..VSsSsSsSV..SSQ.....",
    "..SSs..VSQsSQsSV..sSS.....",
    "..sSS..BBBBbbBBB..SSs.....",
    ".sSSSs.PPPPPPPPP.sSSSs....",
    "..sSs..PPPPPPPPP..sSs.....",
]
B_T_STRAIGHT = [
    "....sQQSNNNNNSQQs.........",
    "..sQQS.VQQSsSQQVSQQQQQsGGG",
    "..QQSS.VQSSsSSQVsSSSSSS.gG",
] + _B_LOW
B_T_UP = [
    "....sQQSNNNNNSQQQQQsGGG...",
    "..sQQS.VQQSsSQQVSSSSS.gG..",
    "..QQSS.VQSSsSSQV..........",
] + _B_LOW
B_T_DOWN = [
    "....sQQSNNNNNSQQs.........",
    "..sQQS.VQQSsSQQV.SQQs.....",
    "..QQSS.VQSSsSSQV.SSQQ.....",
    "..QSSs.VsssSsssV.sSSQ.....",
    "..SSs..VSQsSQsSVSSSSSSsGGG",
    "..QSS..VSsSsSsSV......gG..",
    "..SSs..VSQsSQsSV..........",
    "..sSS..BBBBbbBBB..........",
    ".sSSSs.PPPPPPPPP..........",
    "..sSs..PPPPPPPPP..........",
]
B_L_IDLE = [
    "......PPPPPpPPPP..........",
    "......PPPPP.PPPP..........",
    "......PPPPP.PPPP..........",
    "......PPPPp.PPPp..........",
    "......KKKKK.KKKK..........",
    ".....KKKKKK.KKKKK.........",
    ".....KKKKKK.KKKKK.........",
]
B_L_A = [
    "......PPPPPpPPPP..........",
    ".....PPPPP...PPPP.........",
    "....PPPPP.....PPPP........",
    "....PPPPp.....PPPp........",
    "...KKKKK.......KKKK.......",
    "..KKKKKK.......KKKKK......",
    "..KKKKKK.......KKKKK......",
]
B_L_B = [
    "......PPPPPpPPPP..........",
    ".......PPPPPPPP...........",
    ".......PPPPPPPP...........",
    ".......PPPPpPPp...........",
    ".......KKKKKKKK...........",
    "......KKKKKKKKKK..........",
    "......KKKKKKKKK...........",
]

# Per-body geometry: sprite anchor (left offset when facing right/left, top offset),
# bullet-hit box relative to the feet, gun muzzle offsets, hat height, shadow width, min feet y.
BODY_GEOM = {
    "normal": dict(left=(9, 10), top=24, hitbox=(-5, -23, 11, 23),
                   guns={"up": (8, -13), "straight": (9, -12), "down": (9, -10)},
                   hat_y=-21, shadow=16, min_y=88),
    "brute": dict(left=(12, 15), top=28, hitbox=(-8, -27, 17, 27),
                  guns={"up": (11, -16), "straight": (14, -15), "down": (14, -12)},
                  hat_y=-25, shadow=24, min_y=88),
    "mounted": dict(left=(20, 23), top=40, hitbox=(-17, -37, 36, 37),
                    guns={"up": (7, -27), "straight": (8, -26), "down": (8, -24)},
                    hat_y=-35, shadow=32, min_y=104),
}
BODY_GEOM["lady"] = BODY_GEOM["normal"]
BODY_GEOM["girl"] = BODY_GEOM["normal"]


def body_geom(char):
    return BODY_GEOM[char.get("body", "normal")]


def _horse(c, legs):
    """A horse facing right on a 42x40 canvas. legs: 'stand', 'a' or 'b' (gallop)."""
    s = pygame.Surface((42, 40), SRCALPHA)
    body, mane, hoof = c["body"], c["mane"], (30, 24, 22)
    hi, lo = shade(body, 1.35), shade(body, 0.75)
    pygame.draw.polygon(s, mane, [(7, 19), (3, 21), (1, 29), (3, 31), (6, 24)])
    leg_sets = {
        "stand": [((10, 28), (10, 37)), ((14, 28), (14, 37)), ((27, 28), (27, 37)), ((31, 28), (31, 37))],
        "a": [((10, 28), (6, 37)), ((14, 28), (12, 37)), ((27, 28), (31, 37)), ((31, 28), (35, 36))],
        "b": [((10, 28), (13, 37)), ((14, 28), (17, 37)), ((27, 28), (24, 37)), ((31, 28), (28, 37))],
    }[legs]
    for i, (a, b) in enumerate(leg_sets):
        pygame.draw.line(s, lo if i in (0, 2) else body, a, b, 3)
        s.fill(hoof, (b[0] - 1, b[1], 3, 2))
    pygame.draw.ellipse(s, body, (6, 17, 28, 13))
    pygame.draw.line(s, hi, (11, 18), (28, 18))
    pygame.draw.line(s, lo, (11, 29), (28, 29))
    pygame.draw.polygon(s, body, [(27, 22), (30, 11), (35, 10), (36, 15), (33, 24)])
    pygame.draw.polygon(s, body, [(32, 9), (40, 13), (41, 16), (38, 17), (33, 15)])
    s.fill(lo, (38, 14, 3, 3))
    s.fill(body, (32, 7, 2, 3))
    s.set_at((35, 11), (240, 230, 220))
    pygame.draw.line(s, mane, (31, 9), (27, 19), 2)
    s.fill(c["blanket"], (13, 18, 12, 3))
    s.fill((110, 70, 40), (14, 15, 10, 4))
    s.fill((140, 96, 56), (23, 13, 2, 2))
    return s


def _palette(char):
    col = dict(char["colors"])
    col.setdefault("R", (236, 224, 200))
    col.setdefault("L", (200, 50, 64))
    col["s"] = shade(col["S"], 0.8)
    col["Q"] = shade(col["S"], 1.2)
    col["p"] = shade(col["P"], 0.72)
    col["g"] = shade(col["G"], 0.55)
    col["c"] = shade(col["C"], 0.8)
    return col


def build_couple_ride(hero, girl):
    """The sheriff with Miss Lily riding behind him, facing right. Returns (stand, gallop_a, gallop_b)."""
    hc, gc = _palette(hero), _palette(girl)
    horse = dict(body=(156, 104, 62), mane=(70, 44, 26), blanket=(60, 110, 190))
    sheriff = from_rows(HEAD + T_IDLE, hc)
    lily = from_rows(G_HEAD + F_T_IDLE, gc)
    out = []
    for legs in ("stand", "a", "b"):
        s = _horse(horse, legs)
        s.fill(gc["P"], (10, 17, 7, 4))         # her skirt draped over the horse
        s.fill(gc["P"], (12, 21, 4, 3))
        s.blit(lily, (4, 3))
        s.fill(hc["P"], (18, 18, 3, 5))
        s.fill(hc["K"], (17, 23, 5, 3))
        s.blit(sheriff, (11, 2))
        out.append(outlined(s))
    return out


_char_cache = {}


def build_character(char):
    """Returns {frame_name: (facing_right_surface, facing_left_surface)}."""
    key = char["name"]
    if key in _char_cache:
        return _char_cache[key]
    col = _palette(char)
    body = char.get("body", "normal")

    if body == "mounted":
        horse = char.get("horse", dict(body=(44, 40, 46), mane=(18, 16, 20), blanket=(120, 30, 40)))
        rider = {k: from_rows(HEAD + t, col) for k, t in
                 (("idle", T_IDLE), ("up", T_UP), ("straight", T_STRAIGHT), ("down", T_DOWN))}

        def mk(pose, legs):
            s = _horse(horse, legs)
            s.fill(col["P"], (18, 18, 3, 5))
            s.fill(col["K"], (17, 23, 5, 3))
            s.blit(rider[pose], (11, 2))
            return outlined(s)

        frames = {"idle": mk("idle", "stand"), "walk_a": mk("idle", "a"), "walk_b": mk("idle", "b"),
                  "up": mk("up", "stand"), "straight": mk("straight", "stand"), "down": mk("down", "stand"),
                  "hat": outlined(from_rows(HEAD[:5], col)), "head": outlined(from_rows(HEAD, col))}
    else:
        if body == "brute":
            head, ti, ts, tu, td, li, la, lb = (B_HEAD, B_T_IDLE, B_T_STRAIGHT, B_T_UP, B_T_DOWN,
                                                 B_L_IDLE, B_L_A, B_L_B)
            portrait = [r[4:20] for r in B_HEAD]
            hat_rows = B_HEAD[:6]
        elif body == "girl":
            head, ti, ts, tu, td, li, la, lb = (G_HEAD, F_T_IDLE, F_T_IDLE, F_T_IDLE, F_T_IDLE,
                                                 F_L_IDLE, F_L_A, F_L_B)
            portrait, hat_rows = G_HEAD, G_HEAD[:5]
        elif body == "lady":
            head, ti, ts, tu, td, li, la, lb = (F_HEAD, F_T_IDLE, F_T_STRAIGHT, F_T_UP, F_T_DOWN,
                                                 F_L_IDLE, F_L_A, F_L_B)
            portrait, hat_rows = F_HEAD, F_HEAD[:5]
        else:
            head, ti, ts, tu, td, li, la, lb = HEAD, T_IDLE, T_STRAIGHT, T_UP, T_DOWN, L_IDLE, L_A, L_B
            portrait, hat_rows = HEAD, HEAD[:5]

        def mk(torso, legs):
            return outlined(from_rows(head + torso + legs, col))

        frames = {
            "idle": mk(ti, li), "walk_a": mk(ti, la), "walk_b": mk(ti, lb),
            "up": mk(tu, li), "straight": mk(ts, li), "down": mk(td, li),
            "hat": outlined(from_rows(hat_rows, col)),
            "head": outlined(from_rows(portrait, col)),
        }
    frames["dead"] = pygame.transform.rotate(frames["idle"], 90)
    result = {k: (v, pygame.transform.flip(v, True, False)) for k, v in frames.items()}
    _char_cache[key] = result
    return result


# ----------------------------------------------------------------------------
# Obstacles
# ----------------------------------------------------------------------------
def _cactus():
    s = pygame.Surface((20, 36), SRCALPHA)
    G, D, L = (64, 150, 62), (36, 98, 44), (128, 200, 98)

    def column(x, y0, y1, cw):
        pygame.draw.rect(s, G, (x, y0 + 2, cw, y1 - y0 - 2))
        pygame.draw.rect(s, G, (x + 1, y0, cw - 2, 2))
        pygame.draw.line(s, L, (x + 1, y0 + 2), (x + 1, y1 - 1))
        pygame.draw.line(s, D, (x + cw - 1, y0 + 2), (x + cw - 1, y1 - 1))

    column(7, 0, 36, 7)
    pygame.draw.line(s, D, (10, 3), (10, 35))
    column(2, 9, 22, 4)
    pygame.draw.rect(s, G, (2, 19, 6, 3))
    pygame.draw.line(s, D, (2, 21), (7, 21))
    column(14, 5, 18, 4)
    pygame.draw.rect(s, G, (12, 15, 6, 3))
    pygame.draw.line(s, D, (12, 17), (17, 17))
    for p in ((8, 6), (12, 10), (8, 15), (12, 22), (8, 27), (12, 31), (3, 12), (16, 9), (4, 17)):
        s.set_at(p, (236, 226, 160))
    s.set_at((9, 0), (240, 110, 150))
    s.set_at((10, 0), (250, 150, 180))
    return outlined(s)


def _wagon():
    s = pygame.Surface((52, 34), SRCALPHA)
    canvas, cdark = (236, 228, 200), (196, 186, 156)
    body, bdark = (132, 82, 44), (92, 56, 30)
    pygame.draw.ellipse(s, canvas, (6, 0, 40, 32))
    pygame.draw.ellipse(s, cdark, (6, 0, 40, 32), 1)
    for x in (16, 26, 36):
        pygame.draw.line(s, cdark, (x, 1), (x, 15))
    s.fill((0, 0, 0, 0), (0, 15, 52, 19))
    pygame.draw.rect(s, body, (4, 15, 44, 9))
    pygame.draw.line(s, shade(body, 1.3), (4, 15), (47, 15))
    for y in (18, 21):
        pygame.draw.line(s, bdark, (4, y), (47, y))
    pygame.draw.line(s, bdark, (47, 22), (51, 25))
    for cx in (13, 39):
        pygame.draw.circle(s, (80, 50, 28), (cx, 26), 7, 2)
        for a in range(0, 360, 45):
            r = math.radians(a)
            pygame.draw.line(s, (110, 72, 40), (cx, 26), (cx + int(math.cos(r) * 5), 26 + int(math.sin(r) * 5)))
        pygame.draw.circle(s, (60, 40, 22), (cx, 26), 2)
    return outlined(s)


def _coach():
    s = pygame.Surface((46, 36), SRCALPHA)
    body, dark, trim = (150, 40, 36), (100, 24, 24), (230, 190, 90)
    pygame.draw.rect(s, (90, 60, 34), (8, 0, 30, 5))          # luggage
    pygame.draw.line(s, (60, 40, 22), (8, 2), (37, 2))
    pygame.draw.rect(s, body, (4, 5, 38, 20), border_radius=3)
    pygame.draw.rect(s, trim, (4, 5, 38, 20), 1, border_radius=3)
    pygame.draw.rect(s, (40, 30, 40), (10, 9, 10, 8))           # windows
    pygame.draw.rect(s, (40, 30, 40), (26, 9, 10, 8))
    pygame.draw.line(s, (120, 120, 150), (11, 10), (14, 10))
    pygame.draw.line(s, (120, 120, 150), (27, 10), (30, 10))
    pygame.draw.line(s, dark, (5, 22), (40, 22))
    for cx in (11, 35):
        pygame.draw.circle(s, (70, 44, 24), (cx, 28), 7, 2)
        for a in range(0, 360, 60):
            r = math.radians(a + 15)
            pygame.draw.line(s, (110, 72, 40), (cx, 28), (cx + int(math.cos(r) * 5), 28 + int(math.sin(r) * 5)))
        pygame.draw.circle(s, trim, (cx, 28), 1)
    return outlined(s)


def _barrel():
    s = pygame.Surface((12, 15), SRCALPHA)
    body = (150, 95, 50)
    pygame.draw.rect(s, body, (1, 0, 10, 15), border_radius=3)
    pygame.draw.line(s, shade(body, 0.65), (9, 1), (9, 13))
    pygame.draw.line(s, shade(body, 1.3), (3, 1), (3, 13))
    for y in (3, 10):
        pygame.draw.rect(s, (74, 72, 80), (0, y, 12, 2))
        s.set_at((3, y), (140, 140, 150))
    pygame.draw.ellipse(s, shade(body, 0.75), (2, 0, 8, 3))
    return outlined(s)


def _rock():
    s = pygame.Surface((20, 12), SRCALPHA)
    g = (138, 126, 114)
    pygame.draw.polygon(s, g, [(1, 11), (3, 5), (8, 1), (14, 2), (19, 7), (18, 11)])
    pygame.draw.line(s, shade(g, 1.3), (4, 5), (8, 2))
    pygame.draw.line(s, shade(g, 1.3), (8, 2), (13, 3))
    pygame.draw.line(s, shade(g, 0.7), (2, 11), (18, 11))
    pygame.draw.line(s, shade(g, 0.8), (11, 5), (13, 9))
    return outlined(s)


def _tumbleweed():
    rnd = random.Random(42)
    s = pygame.Surface((13, 13), SRCALPHA)
    for _ in range(16):
        a0 = rnd.uniform(0, math.tau)
        r = rnd.uniform(2, 6)
        rect = (6.5 - r, 6.5 - r, r * 2, r * 2)
        col = rnd.choice(((160, 118, 64), (120, 86, 48), (186, 146, 90)))
        pygame.draw.arc(s, col, rect, a0, a0 + rnd.uniform(1, 3))
    base = outlined(s, (70, 46, 26))
    return [pygame.transform.rotate(base, -a) for a in range(0, 360, 45)]


_obst_cache = {}


def obstacle_sprite(kind):
    if kind not in _obst_cache:
        _obst_cache[kind] = {
            "cactus": _cactus, "wagon": _wagon, "coach": _coach,
            "barrel": _barrel, "rock": _rock, "tumble": _tumbleweed,
        }[kind]()
    return _obst_cache[kind]


_white_cache = {}


def white_version(surf):
    key = id(surf)
    if key not in _white_cache:
        _white_cache[key] = silhouette(surf, (255, 255, 255))
    return _white_cache[key]


# ----------------------------------------------------------------------------
# Effects
# ----------------------------------------------------------------------------
_circles = {}


def soft_circle(r, color, alpha):
    key = (r, color, alpha)
    s = _circles.get(key)
    if s is None:
        s = pygame.Surface((r * 2 + 1, r * 2 + 1), SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (r, r), r)
        _circles[key] = s
    return s


_glows = {}


def glow(r, color):
    """Radial glow for additive blending (night levels)."""
    key = (r, color)
    s = _glows.get(key)
    if s is None:
        s = pygame.Surface((r * 2 + 1, r * 2 + 1))
        for i in range(r, 0, -1):
            f = (1 - i / r) ** 1.6
            pygame.draw.circle(s, shade(color, f), (r, r), i)
        _glows[key] = s
    return s


def muzzle_flash(facing):
    s = pygame.Surface((9, 7), SRCALPHA)
    pygame.draw.polygon(s, (255, 200, 60), [(0, 3), (4, 0), (8, 3), (4, 6)])
    pygame.draw.line(s, (255, 255, 220), (0, 3), (6, 3))
    s.set_at((3, 2), (255, 255, 230))
    s.set_at((3, 4), (255, 255, 230))
    return s if facing > 0 else pygame.transform.flip(s, True, False)


def make_clouds(theme, rnd):
    col = theme.get("cloud")
    if not col:
        return []
    clouds = []
    for _ in range(4):
        w = rnd.randint(26, 50)
        s = pygame.Surface((w, 12), SRCALPHA)
        dark = lerp(col, theme["sky"][0], 0.35)
        for _ in range(6):
            cw = rnd.randint(10, 20)
            cx = rnd.randint(0, w - cw)
            pygame.draw.ellipse(s, dark, (cx, rnd.randint(2, 4), cw, 8))
        for _ in range(5):
            cw = rnd.randint(8, 16)
            cx = rnd.randint(1, w - cw - 1)
            pygame.draw.ellipse(s, col, (cx, rnd.randint(0, 2), cw, 7))
        clouds.append([rnd.uniform(0, W), rnd.uniform(HUD_H + 2, HORIZON - 26), rnd.uniform(3, 8), s])
    return clouds


# ----------------------------------------------------------------------------
# Background
# ----------------------------------------------------------------------------
TOWER_X = 200
CLOCK_POS = (TOWER_X, HORIZON - 25)


def _butte(s, x0, x1, top, color, rnd):
    slope = rnd.randint(3, 8)
    pts = [(x0, HORIZON), (x0 + slope, top + 2), (x0 + slope + 2, top),
           (x1 - slope - 2, top), (x1 - slope, top + 2), (x1, HORIZON)]
    pygame.draw.polygon(s, color, pts)
    pygame.draw.line(s, shade(color, 1.12), (x0 + slope + 2, top), (x1 - slope - 2, top))
    dark = shade(color, 0.88)
    for yy in range(top + 4, HORIZON, 4):
        for xx in range(x0 + slope + 1, x1 - slope):
            if (xx + yy) % 3 == 0:
                s.set_at((xx, yy), dark)


def build_background(theme, seed=1):
    rnd = random.Random(seed)
    s = pygame.Surface((W, H)).convert()
    dither_fill(s, (0, 0, W, HORIZON), theme["sky"][0], theme["sky"][1], steps=10)

    if theme.get("stars"):
        for _ in range(110):
            x, y = rnd.randrange(W), rnd.randrange(HUD_H, HORIZON - 6)
            b = rnd.randint(110, 255)
            s.set_at((x, y), (b, b, min(255, b + 25)))

    body = theme.get("sun") or theme.get("moon")
    if body:
        sx, sy = theme["sun_pos"]
        r = theme["sun_r"]
        halo = lerp(body, theme["sky"][1], 0.45)
        for yy in range(max(0, sy - r * 2), min(HORIZON, sy + r * 2 + 1)):
            for xx in range(max(0, sx - r * 2), min(W, sx + r * 2 + 1)):
                d = math.hypot(xx - sx, yy - sy)
                if r < d <= r * 2 and BAYER[yy % 4][xx % 4] > (d - r) / r * 16:
                    s.set_at((xx, yy), lerp(s.get_at((xx, yy)), halo, 0.5))
        pygame.draw.circle(s, body, (sx, sy), r)
        if theme.get("moon"):
            crater = shade(body, 0.85)
            pygame.draw.circle(s, crater, (sx - r // 3, sy - r // 4), max(1, r // 3))
            pygame.draw.circle(s, crater, (sx + r // 3, sy + r // 3), max(1, r // 4))
        else:
            pygame.draw.circle(s, lerp(body, (255, 255, 255), 0.5), (sx - 1, sy - 1), max(1, r - 3))

    # far buttes
    x = rnd.randint(-30, 0)
    while x < W:
        w = rnd.randint(40, 90)
        if rnd.random() < 0.75:
            _butte(s, x, x + w, HORIZON - rnd.randint(12, 26), theme["far"], rnd)
        x += w + rnd.randint(5, 30)

    # near hills (ragged ridge)
    pts = [(0, HORIZON)]
    h = rnd.randint(4, 10)
    for xx in range(0, W + 8, 8):
        h = max(2, min(13, h + rnd.randint(-3, 3)))
        pts.append((xx, HORIZON - h))
    pts.append((W, HORIZON))
    pygame.draw.polygon(s, theme["near"], pts)

    # little frontier town with the clock tower
    town = theme["town"]
    lit = theme.get("lights")
    for bx, bw, bh in ((140, 16, 14), (158, 20, 10), (180, 10, 13), (212, 12, 16), (226, 18, 11), (246, 14, 13)):
        pygame.draw.rect(s, town, (bx, HORIZON - bh, bw, bh))
        pygame.draw.rect(s, town, (bx + 2, HORIZON - bh - 3, bw - 4, 3))
        for wx in range(bx + 3, bx + bw - 3, 5):
            col = (250, 210, 110) if (lit and rnd.random() < 0.7) else shade(town, 0.6)
            s.fill(col, (wx, HORIZON - bh + 4, 2, 3))
    tx = TOWER_X
    pygame.draw.rect(s, town, (tx - 8, HORIZON - 36, 16, 36))
    pygame.draw.polygon(s, shade(town, 0.85), [(tx - 10, HORIZON - 36), (tx, HORIZON - 48), (tx + 10, HORIZON - 36)])
    s.fill(shade(town, 0.6) if not lit else (250, 210, 110), (tx - 2, HORIZON - 14, 4, 5))
    cx, cy = CLOCK_POS
    pygame.draw.circle(s, (240, 230, 200), (cx, cy), 6)
    pygame.draw.circle(s, (60, 40, 30), (cx, cy), 6, 1)

    # ground
    g0, g1 = theme["ground"]
    dither_fill(s, (0, HORIZON, W, H - HORIZON), g0, g1, steps=8)
    light, dark = shade(g0, 1.08), shade(g1, 0.82)
    for _ in range(700):
        x, y = rnd.randrange(W), rnd.randrange(HORIZON + 1, H)
        s.set_at((x, y), light if rnd.random() < 0.5 else dark)
    for _ in range(30):                     # pebbles
        x, y = rnd.randrange(W), rnd.randrange(HORIZON + 8, H - 6)
        s.fill(shade(g1, 0.7), (x, y + 1, 3, 1))
        s.fill(shade(g0, 1.15), (x, y, 2, 1))
    tuft = lerp((110, 120, 50), g1, 0.4)
    for _ in range(28):                     # scrub grass
        x, y = rnd.randrange(W), rnd.randrange(HORIZON + 10, H - 6)
        for dx in (-2, 0, 2):
            pygame.draw.line(s, tuft, (x, y), (x + dx, y - rnd.randint(2, 4)))
    for _ in range(2):                      # cow skulls, of course
        x = rnd.choice((rnd.randrange(20, 120), rnd.randrange(280, 380)))
        y = rnd.randrange(HORIZON + 20, H - 10)
        bone = (236, 228, 210)
        s.fill(bone, (x, y, 4, 3))
        s.set_at((x - 1, y - 1), bone)
        s.set_at((x + 4, y - 1), bone)
        s.set_at((x + 1, y + 1), (60, 40, 30))

    # fences (the ricochet rails)
    fc = theme["fence"]
    for fx in range(4, W, 18):
        s.fill(shade(fc, 0.7), (fx, HORIZON - 1, 2, 11))
    s.fill(fc, (0, HORIZON + 1, W, 2))
    s.fill(fc, (0, HORIZON + 6, W, 2))
    s.fill(shade(fc, 1.25), (0, HORIZON + 1, W, 1))
    s.fill(fc, (0, H - 4, W, 2))
    s.fill(shade(fc, 1.25), (0, H - 4, W, 1))
    for fx in range(4, W, 18):
        s.fill(shade(fc, 0.7), (fx, H - 6, 2, 6))
    return s


def draw_clock(surf, hours, minutes):
    cx, cy = CLOCK_POS
    pygame.draw.circle(surf, (240, 230, 200), (cx, cy), 5)
    ma = math.radians(minutes * 6 - 90)
    ha = math.radians((hours % 12 + minutes / 60) * 30 - 90)
    pygame.draw.line(surf, (30, 20, 20), (cx, cy), (cx + round(math.cos(ma) * 5), cy + round(math.sin(ma) * 5)))
    pygame.draw.line(surf, (160, 30, 30), (cx, cy), (cx + round(math.cos(ha) * 3), cy + round(math.sin(ha) * 3)))


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
WOOD = (104, 64, 34)


def wood_panel(surf, rect, base=WOOD):
    rect = pygame.Rect(rect)
    surf.fill(base, rect)
    for y in range(rect.y + 5, rect.bottom - 1, 6):
        pygame.draw.line(surf, shade(base, 0.78), (rect.x + 1, y), (rect.right - 2, y))
    for i in range(0, rect.w, 23):
        s = (rect.x + 7 + i * 3) % max(1, rect.w - 4)
        surf.fill(shade(base, 0.85), (rect.x + 2 + s, rect.y + 2 + (i % 4) * 6, 4, 1))
    pygame.draw.rect(surf, shade(base, 0.45), rect, 1)
    pygame.draw.line(surf, shade(base, 1.35), (rect.x + 1, rect.y + 1), (rect.right - 2, rect.y + 1))
    for nx, ny in ((rect.x + 3, rect.y + 3), (rect.right - 4, rect.y + 3),
                   (rect.x + 3, rect.bottom - 4), (rect.right - 4, rect.bottom - 4)):
        surf.set_at((nx, ny), (200, 200, 190))


def hud_bar():
    s = pygame.Surface((W, HUD_H)).convert()
    wood_panel(s, (0, 0, W, HUD_H))
    return s


def bullet_icon(surf, x, y, full=True):
    if full:
        surf.fill((206, 160, 60), (x, y + 1, 2, 4))
        surf.fill((240, 214, 120), (x, y + 1, 1, 4))
        surf.fill((150, 150, 160), (x, y, 2, 1))
    else:
        surf.fill((60, 36, 20), (x, y + 1, 2, 4))


def star(surf, x, y, filled):
    col = (250, 210, 80) if filled else (70, 44, 24)
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36)
        r = 4 if i % 2 == 0 else 1.8
        pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
    pygame.draw.polygon(surf, col, pts)
    if filled:
        surf.set_at((x - 1, y - 1), (255, 250, 200))


def draw_poster(surf, rect, char, bounty, locked=False, big=False, name_size=None):
    """A sun-bleached WANTED poster with the outlaw's portrait."""
    rect = pygame.Rect(rect)
    paper, edge = (226, 200, 148), (176, 136, 86)
    surf.fill(edge, rect)
    surf.fill(paper, rect.inflate(-2, -2))
    for y in range(rect.y + 1, rect.bottom - 1):
        for x in (rect.x + 1, rect.x + 2, rect.right - 3, rect.right - 2):
            if BAYER[y % 4][x % 4] < 7:
                surf.set_at((x, y), shade(paper, 0.88))
    ink = (70, 40, 22)
    text(surf, "WANTED", 22 if big else 12, (rect.centerx, rect.y + (12 if big else 8)), ink, shadow=None)
    scale = 4 if big else 2
    pw, ph = 20 * scale, 12 * scale
    pr = pygame.Rect(0, 0, pw + 4, ph + 4)
    pr.midtop = (rect.centerx, rect.y + (24 if big else 15))
    surf.fill((200, 168, 116), pr)
    pygame.draw.rect(surf, ink, pr, 1)
    head = build_character(char)["head"][0]
    head = pygame.transform.scale(head, (head.get_width() * scale, head.get_height() * scale))
    if locked:
        head = silhouette(head, (60, 40, 26))
    surf.blit(head, head.get_rect(center=pr.center))
    if locked:
        text(surf, "?", 26 if big else 18, pr.center, (240, 220, 170), shadow=ink)
    if big:
        name = "??????" if locked else char["name"]
        text(surf, name, name_size or 16, (rect.centerx, pr.bottom + 9), ink, shadow=None)
    else:
        text(surf, "REWARD", 12, (rect.centerx, rect.bottom - 18), ink, shadow=None)
    text(surf, "$%d" % bounty, 20 if big else 12, (rect.centerx, rect.bottom - (12 if big else 8)),
         (140, 30, 20), shadow=None)
    surf.fill((150, 150, 150), (rect.centerx - 1, rect.y + 1, 2, 2))
