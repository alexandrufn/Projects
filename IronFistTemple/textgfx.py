"""Pixel font and text helpers (shared look with the other game in this folder)."""
import pygame

SRCALPHA = pygame.SRCALPHA
OUTLINE = (22, 12, 10)

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


