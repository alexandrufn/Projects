"""Procedural 16-bit style graphics: pose-driven fighters, props, city backgrounds, effects and HUD.

Fighters are drawn from a handful of joint targets (hip, chest, head, hands, feet) with two-bone
IK for arms and legs, so any pose can be animated for any character, scale and held weapon.
"""
import math
import random

import pygame

from config import W, H, FLOOR_Y, HUD_H, THEMES
from textgfx import lerp, shade, text, fancy_text, wrap, font, text_width, dither_fill, bitmap_text  # noqa: F401

SRCALPHA = pygame.SRCALPHA
OUT = (16, 10, 20)
THIGH = SHIN = 12.0
UARM = FARM = 8.0


# ----------------------------------------------------------------------------
# Rigging
# ----------------------------------------------------------------------------
def ik(p0, tgt, l1, l2, bend):
    dx, dy = tgt[0] - p0[0], tgt[1] - p0[1]
    d = math.hypot(dx, dy)
    if d < 1e-3:
        dx, dy, d = 0.0, 1.0, 1.0
    reach = l1 + l2 - 0.2
    if d > reach:
        k = reach / d
        tx, ty, d = p0[0] + dx * k, p0[1] + dy * k, reach
    else:
        tx, ty = tgt
    ux, uy = (tx - p0[0]) / d, (ty - p0[1]) / d
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    return (p0[0] + ux * a - uy * h * bend, p0[1] + uy * a + ux * h * bend), (tx, ty)


def _pose(hip, chest, head, hf, hb, ff, fb, **kw):
    d = dict(hip=hip, chest=chest, head=head, hf=hf, hb=hb, ff=ff, fb=fb)
    d.update(kw)
    return d


def make_pose(name, ph=0.0):
    """Joint targets (x forward, y up is negative), feet at y=0."""
    b = math.sin(ph * math.tau)
    if name == "idle":
        return _pose((0, -22), (0, -35 + b * 0.8), (1, -42 + b * 0.8), (9, -31 + b * 0.6), (4, -30 + b * 0.6),
                     (6, 0), (-6, 0))
    if name in ("walk", "cwalk"):
        a = ph * math.tau
        sw = math.sin(a) * 9
        lf, lb = max(0, math.cos(a)) * 5, max(0, -math.cos(a)) * 5
        bob = -abs(math.sin(a)) * 1.3
        if name == "cwalk":
            return _pose((0, -22 + bob), (0, -35 + bob), (1, -42 + bob), (5, -52 + bob), (-3, -52 + bob),
                         (sw, -lf), (-sw, -lb), carry=1)
        return _pose((0, -22 + bob), (1, -35 + bob), (2, -42 + bob), (9, -30 + math.sin(a) * 2),
                     (4, -29 - math.sin(a) * 2), (sw, -lf), (-sw, -lb))
    if name == "crouch":
        return _pose((-1, -12), (3, -23), (5, -30), (10, -19), (5, -15), (9, 0), (-7, 0))
    if name == "jump":
        return _pose((0, -20), (0, -33), (1, -40), (11, -33), (5, -35), (8, -9), (-3, -4))
    if name == "punch_w":
        return _pose((0, -22), (-1, -35), (0, -42), (2, -31), (8, -31), (8, 0), (-8, 0))
    if name == "punch":
        return _pose((0, -22), (5, -35), (7, -42), (23, -34), (-2, -29), (10, 0), (-8, 0))
    if name == "cross":
        return _pose((1, -22), (6, -35), (8, -42), (6, -31), (22, -34), (10, 0), (-9, 0))
    if name == "upper_w":
        return _pose((0, -18), (2, -30), (4, -37), (7, -21), (6, -31), (8, 0), (-8, 0))
    if name == "upper":
        return _pose((1, -23), (4, -37), (6, -44), (14, -52), (2, -31), (8, -2), (-7, 0))
    if name == "kick_w":
        return _pose((0, -22), (-3, -35), (-3, -42), (8, -33), (-3, -33), (8, -24), (-5, 0))
    if name == "kick":
        return _pose((1, -22), (-4, -35), (-4, -42), (8, -37), (-10, -33), (25, -31), (-5, 0))
    if name == "rkick":
        return _pose((1, -23), (-7, -34), (-8, -41), (3, -39), (-13, -31), (26, -40), (-5, 0))
    if name == "jkick":
        return _pose((0, -21), (-4, -33), (-4, -40), (6, -36), (-9, -34), (22, -24), (-6, -10))
    if name == "elbow":
        return _pose((0, -22), (-3, -35), (-1, -42), (6, -30), (-15, -34), (6, 0), (-10, 0))
    if name == "spin":
        if ph < 0.5:
            return _pose((0, -22), (-4, -35), (-4, -42), (8, -37), (-10, -33), (26, -33), (-4, 0))
        return _pose((0, -22), (4, -35), (4, -42), (10, -33), (-8, -37), (4, 0), (-26, -33))
    if name == "knee":
        return _pose((1, -24), (4, -36), (7, -42), (14, -36), (12, -33), (13, -21), (-5, 0))
    if name == "grab":
        return _pose((0, -22), (2, -35), (3, -42), (16, -33), (14, -29), (6, 0), (-6, 0))
    if name == "held":
        return _pose((-1, -21), (5, -30), (9, -33), (6, -20), (2, -20), (4, 0), (-6, 0))
    if name == "gripped":
        return _pose((-1, -22), (-3, -34), (-4, -40), (4, -30), (-6, -30), (5, 0), (-7, 0))
    if name == "throw_hi":
        return _pose((0, -22), (-2, -35), (-2, -42), (6, -50), (-4, -27), (7, 0), (-7, 0))
    if name == "throw":
        return _pose((0, -22), (4, -35), (6, -42), (19, -34), (-3, -27), (8, 0), (-7, 0))
    if name == "hurt":
        return _pose((-1, -22), (-5, -34), (-8, -40), (3, -38), (-7, -36), (4, 0), (-9, 0))
    if name == "hurt2":
        return _pose((-1, -21), (3, -31), (5, -36), (5, -24), (-1, -24), (6, 0), (-7, 0))
    if name == "fall":
        return _pose((0, -20), (-10, -28), (-16, -31), (-6, -40), (-12, -38), (10, -10), (6, -16))
    if name == "lie":
        return _pose((-9, -6), (-22, -7), (-31, -6), (-24, -13), (-30, -3), (8, -3), (5, -9))
    if name == "getup":
        return _pose((-1, -12), (3, -23), (5, -30), (10, -12), (2, -10), (9, 0), (-7, 0))
    if name == "victory":
        return _pose((0, -22), (0, -35), (1, -42), (8, -52), (-6, -52), (7, 0), (-7, 0))
    if name == "pump":
        return _pose((0, -22), (0, -35), (1, -42), (6, -55), (2, -30), (6, 0), (-7, 0))
    if name == "block":
        return _pose((-1, -21), (-1, -34), (0, -41), (10, -37), (8, -33), (6, 0), (-6, 0))
    if name == "taunt":
        return _pose((0, -22), (-1, -35), (0, -42), (16, -36 + b * 2), (-6, -24), (7, 0), (-7, 0))
    if name == "dash_w":
        return _pose((-1, -19), (-4, -31), (-4, -38), (-2, -26), (5, -29), (8, 0), (-10, 0))
    if name == "dash":
        return _pose((2, -20), (10, -31), (15, -36), (26, -31), (2, -24), (9, -4), (-13, -3))
    if name == "slam_w":
        return _pose((0, -22), (-3, -35), (-3, -42), (4, -52), (0, -52), (6, 0), (-6, 0))
    if name == "slam":
        return _pose((2, -15), (8, -26), (11, -32), (15, -9), (11, -7), (10, 0), (-8, 0))
    if name == "headbutt":
        return _pose((2, -22), (8, -34), (14, -38), (10, -30), (6, -28), (9, 0), (-8, 0))
    if name == "swing_w":
        return _pose((0, -22), (-3, -35), (-2, -42), (-2, -44), (-5, -42), (8, 0), (-8, 0), wdir=(-0.5, -1.0))
    if name == "swing":
        return _pose((1, -21), (6, -34), (8, -41), (18, -30), (14, -30), (10, 0), (-9, 0), wdir=(1.0, 0.25))
    if name == "stab_w":
        return _pose((-1, -22), (-3, -35), (-3, -42), (0, -31), (6, -31), (8, 0), (-8, 0), wdir=(1.0, -0.1))
    if name == "stab":
        return _pose((1, -22), (6, -35), (8, -42), (22, -33), (-2, -29), (11, 0), (-9, 0), wdir=(1.0, 0.0))
    if name == "lift":
        return _pose((0, -22), (0, -35), (1, -42), (5, -52), (-3, -52), (6, 0), (-6, 0), carry=1)
    if name == "toss":
        return _pose((1, -22), (5, -35), (7, -42), (16, -46), (11, -44), (9, 0), (-8, 0))
    if name == "whip_w":
        return _pose((0, -22), (-4, -35), (-4, -42), (-8, -46), (4, -30), (8, 0), (-8, 0), chain="back")
    if name == "whip":
        return _pose((1, -22), (6, -35), (8, -42), (18, -34), (-2, -29), (11, 0), (-8, 0), chain="out")
    if name == "chainspin":
        return _pose((0, -22), (0, -35), (1, -42), (10, -40), (-6, -30), (8, 0), (-8, 0), chain="spin",
                     cph=ph)
    if name == "kneel":
        return _pose((-2, -12), (-1, -25), (0, -32), (-7, -18), (-9, -17), (8, -4), (-8, 0))
    if name == "cheer":
        return _pose((0, -24 + b), (0, -37 + b), (1, -44 + b), (7, -55 + b), (-5, -55 + b), (6, 0), (-6, 0))
    raise KeyError(name)


# Pre-quantised animation phases
PHASES = {"idle": 4, "walk": 8, "cwalk": 8, "spin": 2, "chainspin": 8, "taunt": 4, "cheer": 4}

WEAPON_LEN = {"bat": 17, "pipe": 19, "knife": 7, "katana": 24}
WEAPON_COL = {"bat": ((170, 112, 58), (220, 170, 110)), "pipe": ((120, 128, 140), (210, 220, 230)),
              "knife": ((190, 200, 214), (250, 252, 255)), "katana": ((180, 190, 210), (250, 252, 255))}


# ----------------------------------------------------------------------------
# Fighter drawing
# ----------------------------------------------------------------------------
def _limb(surf, pts, w, col, hi=None):
    pygame.draw.lines(surf, col, False, pts, w)
    for p in pts:
        pygame.draw.circle(surf, col, (int(p[0]), int(p[1])), max(1, w // 2))
    if hi is not None and w >= 3:
        pygame.draw.line(surf, hi, (pts[0][0] - 1, pts[0][1]), (pts[1][0] - 1, pts[1][1]), 1)


def outlined(surf, color=OUT):
    w, h = surf.get_size()
    out = pygame.Surface((w + 2, h + 2), SRCALPHA)
    mask = pygame.mask.from_surface(surf, 40)
    sil = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2), (0, 0), (2, 2), (0, 2), (2, 0)):
        out.blit(sil, (dx, dy))
    out.blit(surf, (1, 1))
    return out


def _draw_weapon(surf, pose, weapon, hand, s, pal):
    Wd = lambda w: max(1, int(round(w * s)))  # noqa: E731
    if weapon in WEAPON_LEN:
        dx, dy = pose.get("wdir") or {"knife": (1.0, -0.25), "katana": (0.75, -0.7)}.get(weapon, (0.35, -1.0))
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        L = WEAPON_LEN[weapon] * s
        base, hi = WEAPON_COL[weapon]
        tail = (hand[0] - dx * 3 * s, hand[1] - dy * 3 * s)
        tip = (hand[0] + dx * L, hand[1] + dy * L)
        if weapon == "bat":
            mid = (hand[0] + dx * L * 0.45, hand[1] + dy * L * 0.45)
            pygame.draw.line(surf, base, tail, mid, Wd(2))
            pygame.draw.line(surf, base, mid, tip, Wd(3.6))
            pygame.draw.line(surf, hi, (mid[0], mid[1] - 1), (tip[0], tip[1] - 1), 1)
        elif weapon == "katana":
            pygame.draw.line(surf, (40, 30, 30), tail, (hand[0] + dx * 3 * s, hand[1] + dy * 3 * s), Wd(2.4))
            pygame.draw.line(surf, (230, 190, 80), (hand[0] + dx * 3 * s - dy * 2 * s, hand[1] + dy * 3 * s + dx * 2 * s),
                             (hand[0] + dx * 3 * s + dy * 2 * s, hand[1] + dy * 3 * s - dx * 2 * s), Wd(1.4))
            pygame.draw.line(surf, base, (hand[0] + dx * 4 * s, hand[1] + dy * 4 * s), tip, Wd(2))
            pygame.draw.line(surf, hi, (hand[0] + dx * 4 * s, hand[1] + dy * 4 * s - 1), tip, 1)
        else:
            w = 1.6 if weapon == "knife" else 2.6
            if weapon == "knife":
                pygame.draw.line(surf, (90, 50, 30), tail, hand, Wd(2.2))
            pygame.draw.line(surf, base, hand if weapon == "knife" else tail, tip, Wd(w))
            pygame.draw.line(surf, hi, (hand[0], hand[1] - 1), (tip[0], tip[1] - 1), 1)
    elif weapon == "chain":
        mode = pose.get("chain")
        metal = pal["metal"]
        if mode == "out":
            pts = [(hand[0] + i * 4 * s, hand[1] + math.sin(i * 1.3) * 1.5 * s + i * 0.15 * s) for i in range(12)]
        elif mode == "back":
            pts = [(hand[0] - math.sin(i * 0.4) * 9 * s, hand[1] - i * 1.6 * s + math.cos(i * 0.4) * 2) for i in range(9)]
        elif mode == "spin":
            a = pose.get("cph", 0) * math.tau
            pts = [(hand[0] + math.cos(a) * i * 4 * s, hand[1] + math.sin(a) * i * 1.2 * s) for i in range(11)]
        else:
            pts = [(hand[0] + math.sin(i * 0.7) * 1.5, hand[1] + i * 2.2 * s) for i in range(7)]
        for i, p in enumerate(pts):
            pygame.draw.circle(surf, metal if i % 2 else shade(metal, 0.7), (int(p[0]), int(p[1])), Wd(1.3))


def draw_figure(pose, pal, ex, s, weapon=None):
    CW, CH = int(150 * s), int(118 * s)
    AX, AY = int(75 * s), int(102 * s)
    surf = pygame.Surface((CW, CH), SRCALPHA)

    def P(p):
        return (AX + p[0] * s, AY + p[1] * s)

    def Wd(w):
        return max(1, int(round(w * s)))

    hip, chest, head = P(pose["hip"]), P(pose["chest"]), P(pose["head"])
    skin, top, top2, pants = pal["skin"], pal["top"], pal["top2"], pal["pants"]
    top_d, pants_d, skin_d = shade(top, 0.72), shade(pants, 0.72), shade(skin, 0.78)
    bare = "bare" in ex
    armless = bare or "vest" in ex
    sh_f = (chest[0] + 1 * s, chest[1] + 2 * s)
    sh_b = (chest[0] - 1 * s, chest[1] + 2 * s)
    knee_f, foot_f = ik((hip[0] + 2 * s, hip[1]), P(pose["ff"]), THIGH * s, SHIN * s, -1)
    knee_b, foot_b = ik((hip[0] - 2 * s, hip[1]), P(pose["fb"]), THIGH * s, SHIN * s, -1)
    el_f, hand_f = ik(sh_f, P(pose["hf"]), UARM * s, FARM * s, 1)
    el_b, hand_b = ik(sh_b, P(pose["hb"]), UARM * s, FARM * s, 1)

    if "long" in ex:
        hc = pal["hair"]
        pygame.draw.polygon(surf, shade(hc, 0.8), [(head[0] - 5 * s, head[1] - 3 * s), (head[0] + 1 * s, head[1] - 4 * s),
                                                   (head[0] - 3 * s, head[1] + 10 * s), (head[0] - 9 * s, head[1] + 9 * s)])
    if "coat" in ex:
        tail = [(hip[0] - 5 * s, hip[1] - 2 * s), (hip[0] + 4 * s, hip[1] - 2 * s),
                ((knee_f[0] + knee_b[0]) / 2 + 2 * s, max(knee_f[1], knee_b[1]) + 3 * s),
                ((knee_f[0] + knee_b[0]) / 2 - 12 * s, max(knee_f[1], knee_b[1]) + 2 * s)]
        pygame.draw.polygon(surf, top_d, tail)
        pygame.draw.line(surf, pal["top2"], tail[2], tail[3], 1)

    # back arm / back leg
    sleeve_b = skin_d if armless else top_d
    _limb(surf, [sh_b, el_b], Wd(3.4), sleeve_b)
    _limb(surf, [el_b, hand_b], Wd(3.0), skin_d if (armless or "jacket" not in ex and "coat" not in ex) else top_d)
    pygame.draw.circle(surf, skin_d, (int(hand_b[0]), int(hand_b[1])), Wd(2.2))
    _limb(surf, [(hip[0] - 2 * s, hip[1]), knee_b, foot_b], Wd(4.2), pants_d)
    shoe = pal["shoe"]
    pygame.draw.rect(surf, shade(shoe, 0.8), (int(foot_b[0] - 2 * s), int(foot_b[1] - 3 * s), Wd(7), Wd(3.4)))

    # torso
    tp = [(chest[0] - 4.5 * s, chest[1] - 1 * s), (chest[0] + 4.5 * s, chest[1] - 1 * s),
          (hip[0] + 4 * s, hip[1]), (hip[0] - 4 * s, hip[1])]
    if bare:
        pygame.draw.polygon(surf, skin, tp)
        mid = ((tp[0][0] + tp[1][0]) / 2, (tp[0][1] + tp[2][1]) / 2)
        pygame.draw.line(surf, skin_d, (mid[0] + 1 * s, tp[0][1] + 3 * s), (hip[0] + 1 * s, hip[1] - 2 * s), 1)
        pygame.draw.line(surf, shade(skin, 1.15), (tp[0][0] + 1 * s, tp[0][1] + 1 * s), (tp[0][0] + 1.5 * s, hip[1] - 3 * s), 1)
        pygame.draw.line(surf, skin_d, (chest[0] - 2 * s, chest[1] + 4 * s), (chest[0] + 3 * s, chest[1] + 4 * s), 1)
    else:
        pygame.draw.polygon(surf, top, tp)
        pygame.draw.line(surf, shade(top, 1.25), tp[0], tp[3], 1)
        pygame.draw.line(surf, top_d, tp[1], tp[2], 1)
        if "jacket" in ex or "coat" in ex:
            inner = [(chest[0] + 0.5 * s, chest[1] - 1 * s), (chest[0] + 4 * s, chest[1] - 1 * s),
                     (hip[0] + 3 * s, hip[1] - 1 * s), (hip[0] + 0.5 * s, hip[1] - 1 * s)]
            pygame.draw.polygon(surf, top2, inner)
            pygame.draw.line(surf, shade(top, 1.35), (chest[0] + 0.5 * s, chest[1]), (hip[0] + 0.5 * s, hip[1] - 1 * s), 1)
            pygame.draw.line(surf, shade(top, 1.2), (chest[0] - 3 * s, chest[1] - 1 * s), (chest[0] + 1 * s, chest[1] + 4 * s), 1)
        if "vest" in ex:
            pygame.draw.line(surf, top2 if top2 != top else shade(top, 0.6), (chest[0] + 1 * s, chest[1] - 1 * s),
                             (hip[0] + 1 * s, hip[1] - 1 * s), 1)
    by = hip[1] - 2 * s
    pygame.draw.rect(surf, pal["belt"], (int(hip[0] - 4 * s), int(by), Wd(8.5), Wd(2.4)))
    pygame.draw.rect(surf, (220, 200, 120), (int(hip[0] + 1 * s), int(by), Wd(2), Wd(2.4)))
    _limb(surf, [(hip[0] + 2 * s, hip[1]), knee_f, foot_f], Wd(4.6), pants, shade(pants, 1.25))
    pygame.draw.rect(surf, shoe, (int(foot_f[0] - 2 * s), int(foot_f[1] - 3 * s), Wd(7.5), Wd(3.6)))
    pygame.draw.line(surf, shade(shoe, 1.4) if shoe[0] < 200 else (255, 255, 255),
                     (foot_f[0] - 1 * s, foot_f[1] - 3 * s), (foot_f[0] + 5 * s, foot_f[1] - 3 * s), 1)

    if "pads" in ex:
        for sp, c in ((sh_b, (70, 64, 70)), (sh_f, (96, 90, 100))):
            pygame.draw.circle(surf, c, (int(sp[0]), int(sp[1] - 1 * s)), Wd(3.8))
            pygame.draw.circle(surf, (210, 210, 220), (int(sp[0] - 1 * s), int(sp[1] - 3 * s)), max(1, Wd(1.0)))

    # head
    hr = Wd(5.2)
    hx, hy = int(head[0]), int(head[1])
    pygame.draw.rect(surf, skin, (int(head[0] - 1.5 * s), int(head[1] + hr - 1), Wd(4), Wd(3)))        # neck
    pygame.draw.circle(surf, skin, (hx, hy), hr)
    pygame.draw.circle(surf, skin_d, (int(head[0] - 2 * s), int(head[1] + 1 * s)), max(1, hr - 2), 1)
    pygame.draw.rect(surf, skin, (int(head[0] + 3.5 * s), int(head[1] + 0 * s), Wd(2.2), Wd(2.2)))   # nose
    hair = pal["hair"]
    if "bald" not in ex:
        pygame.draw.circle(surf, hair, (int(head[0] - 0.5 * s), int(head[1] - 0.5 * s)), hr + 1, 0, True, False, False, False)
        pygame.draw.circle(surf, hair, (int(head[0] - 1 * s), int(head[1] - 0.5 * s)), hr + 1, 0, True, False, False, False)
        pygame.draw.rect(surf, hair, (int(head[0] - 6 * s), int(head[1] - 3 * s), Wd(4), Wd(7)))
    else:
        pygame.draw.circle(surf, shade(skin, 1.18), (int(head[0] - 1 * s), int(head[1] - 3 * s)), max(1, Wd(1.4)))
    if "spiky" in ex:
        for k in range(4):
            bx = head[0] - 5 * s + k * 3 * s
            pygame.draw.polygon(surf, hair, [(bx, head[1] - 3 * s), (bx + 3 * s, head[1] - 3 * s),
                                             (bx - 2 * s + k * 0.5 * s, head[1] - 10 * s)])
        pygame.draw.line(surf, shade(hair, 1.6), (head[0] - 3 * s, head[1] - 5 * s), (head[0] + 1 * s, head[1] - 5 * s), 1)
    if "mohawk" in ex:
        pygame.draw.polygon(surf, hair, [(head[0] - 6 * s, head[1] - 2 * s), (head[0] + 3 * s, head[1] - 5 * s),
                                         (head[0] + 1 * s, head[1] - 12 * s), (head[0] - 5 * s, head[1] - 11 * s),
                                         (head[0] - 9 * s, head[1] - 6 * s)])
        pygame.draw.line(surf, shade(hair, 1.4), (head[0] - 5 * s, head[1] - 10 * s), (head[0] + 1 * s, head[1] - 11 * s), 1)
    if "ponytail" in ex:
        sway = math.sin(pose["chest"][0] * 0.5) * 2
        pygame.draw.line(surf, hair, (head[0] - 4 * s, head[1] - 3 * s), (head[0] - 10 * s, head[1] + (4 + sway) * s), Wd(3))
        pygame.draw.line(surf, shade(hair, 1.5), (head[0] - 5 * s, head[1] - 3 * s),
                         (head[0] - 10 * s, head[1] + (3 + sway) * s), 1)
    if "cap" in ex:
        cc = pal["accent"]
        pygame.draw.circle(surf, cc, (int(head[0] - 0.5 * s), int(head[1] - 1 * s)), hr + 1, 0, True, True, False, False)
        pygame.draw.rect(surf, shade(cc, 0.7), (int(head[0] + 1 * s), int(head[1] - 2.5 * s), Wd(7), Wd(1.8)))
        pygame.draw.line(surf, shade(cc, 1.3), (head[0] - 4 * s, head[1] - 4 * s), (head[0] + 2 * s, head[1] - 5 * s), 1)
    if "beard" in ex:
        bc = hair if hair[0] < 200 else (220, 220, 225)
        pygame.draw.polygon(surf, bc, [(head[0] - 1 * s, head[1] + 2 * s), (head[0] + 5 * s, head[1] + 2 * s),
                                       (head[0] + 4 * s, head[1] + 6 * s), (head[0] + 0 * s, head[1] + 6 * s)])
    if "band" in ex:
        band = pal["accent"]
        pygame.draw.line(surf, band, (head[0] - 5.5 * s, head[1] - 2.5 * s), (head[0] + 5.5 * s, head[1] - 2.5 * s), Wd(1.8))
        fl = math.sin(pose["chest"][0] * 0.4 + pose["head"][1]) * 1.5
        pygame.draw.line(surf, band, (head[0] - 5 * s, head[1] - 2.5 * s), (head[0] - 10 * s, head[1] + (-1 + fl) * s), 1)
    # eye
    ey = (int(head[0] + 2.4 * s), int(head[1] - 0.4 * s))
    if "shades" in ex:
        surf.fill((14, 14, 20), (ey[0] - Wd(2.5), ey[1] - 1, Wd(6), Wd(2.2)))
        surf.fill((120, 140, 200), (ey[0] + Wd(1), ey[1] - 1, 1, 1))
    else:
        surf.fill((250, 250, 250), (ey[0] - (1 if s > 1.2 else 0), ey[1], Wd(2.4), Wd(1.6)))
        surf.fill((20, 12, 14), (ey[0] + Wd(1), ey[1], max(1, Wd(1.4)), Wd(1.6)))
        pygame.draw.line(surf, (30, 16, 18), (ey[0] - 1, ey[1] - max(1, int(s)) - 1), (ey[0] + Wd(3), ey[1] - max(1, int(s)) - 1), 1)

    # carried crate / barrel above the head
    if pose.get("carry") and weapon in ("crate", "barrel"):
        img = prop(weapon)
        c = ((hand_f[0] + hand_b[0]) / 2, min(hand_f[1], hand_b[1]) - 5 * s)
        surf.blit(img, img.get_rect(center=(int(c[0]), int(c[1]))))

    # front arm
    sleeve_f = skin if armless else top
    _limb(surf, [sh_f, el_f], Wd(3.8), sleeve_f, shade(sleeve_f, 1.25))
    fore = skin if (armless or ("jacket" not in ex and "coat" not in ex)) else top
    _limb(surf, [el_f, hand_f], Wd(3.2), fore, shade(fore, 1.15))
    if "jacket" in ex or "coat" in ex:
        pygame.draw.circle(surf, top2 if "coat" in ex else shade(top, 0.8),
                           (int(el_f[0] * 0.2 + hand_f[0] * 0.8), int(el_f[1] * 0.2 + hand_f[1] * 0.8)), max(1, Wd(1.8)))
    pygame.draw.circle(surf, skin, (int(hand_f[0]), int(hand_f[1])), Wd(2.6))
    pygame.draw.circle(surf, shade(skin, 1.2), (int(hand_f[0] - 1), int(hand_f[1] - 1)), max(1, Wd(1)))

    if weapon and weapon not in ("crate", "barrel"):
        _draw_weapon(surf, pose, weapon, hand_f, s, pal)
    return outlined(surf), (AX + 1, AY + 1)


_frame_cache = {}
_white_cache = {}


def frame(ckey, cdef, pose_name, ph=0.0, flip=False, weapon=None):
    """Cached figure frame -> (surface, anchor). `flip` mirrors for facing left."""
    n = PHASES.get(pose_name, 1)
    q = int(ph * n) % n if n > 1 else 0
    key = (ckey, pose_name, q, flip, weapon)
    r = _frame_cache.get(key)
    if r is None:
        base_key = (ckey, pose_name, q, False, weapon)
        base = _frame_cache.get(base_key)
        if base is None:
            pose = make_pose(pose_name, q / n if n > 1 else 0.0)
            base = draw_figure(pose, cdef["pal"], cdef["ex"], cdef["scale"], weapon)
            _frame_cache[base_key] = base
        if not flip:
            return base
        surf, (ax, ay) = base
        r = (pygame.transform.flip(surf, True, False), (surf.get_width() - ax, ay))
        _frame_cache[key] = r
    return r


def white(surf):
    key = id(surf)
    w = _white_cache.get(key)
    if w is None:
        w = pygame.mask.from_surface(surf, 40).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        _white_cache[key] = w
    return w


def tinted(surf, color):
    key = (id(surf), color)
    w = _white_cache.get(key)
    if w is None:
        w = surf.copy()
        w.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
        _white_cache[key] = w
    return w


# ----------------------------------------------------------------------------
# Props, pickups and projectiles
# ----------------------------------------------------------------------------
_prop = {}


def prop(kind, k=0):
    key = (kind, k)
    if key in _prop:
        return _prop[key]
    if kind == "crate":
        s = pygame.Surface((17, 15), SRCALPHA)
        s.fill((176, 120, 64))
        for y in (0, 7, 14):
            pygame.draw.line(s, (120, 76, 40), (0, y), (16, y))
        pygame.draw.line(s, (120, 76, 40), (0, 0), (16, 14), 2)
        pygame.draw.rect(s, (130, 84, 44), (0, 0, 17, 15), 1)
        pygame.draw.line(s, (220, 170, 110), (1, 1), (15, 1))
    elif kind == "barrel":
        s = pygame.Surface((14, 18), SRCALPHA)
        pygame.draw.ellipse(s, (60, 110, 150), (0, 0, 14, 18))
        pygame.draw.rect(s, (60, 110, 150), (0, 3, 14, 12))
        for y in (3, 9, 14):
            pygame.draw.line(s, (40, 70, 100), (0, y), (13, y), 2)
        pygame.draw.line(s, (130, 180, 220), (3, 2), (3, 16))
        pygame.draw.ellipse(s, (90, 140, 180), (1, 0, 12, 4))
    elif kind in ("bat", "pipe"):
        s = pygame.Surface((22, 6), SRCALPHA)
        base, hi = WEAPON_COL[kind]
        if kind == "bat":
            pygame.draw.line(s, base, (1, 3), (8, 3), 2)
            pygame.draw.line(s, base, (8, 3), (20, 2), 4)
            pygame.draw.line(s, hi, (9, 1), (19, 1))
        else:
            pygame.draw.line(s, base, (1, 3), (20, 3), 3)
            pygame.draw.line(s, hi, (1, 2), (20, 2))
            pygame.draw.rect(s, (90, 96, 106), (18, 1, 3, 5))
    elif kind in ("knife", "eknife"):
        s = pygame.Surface((13, 5), SRCALPHA)
        pygame.draw.polygon(s, (230, 238, 250), [(0, 2), (8, 0), (12, 2), (8, 4)] if kind == "eknife" else
                            [(4, 1), (12, 2), (4, 3)])
        if kind == "knife":
            pygame.draw.rect(s, (110, 60, 40), (0, 1, 4, 3))
        else:
            pygame.draw.line(s, (130, 140, 170), (2, 3), (10, 3), 1)
            pygame.draw.rect(s, (110, 60, 40), (8, 0, 2, 5))
    elif kind == "star":
        s = pygame.Surface((11, 11), SRCALPHA)
        c = (5, 5)
        for j in range(4):
            a = j * math.pi / 2 + k * math.pi / 8
            pygame.draw.polygon(s, (230, 236, 250), [c, (c[0] + math.cos(a) * 5, c[1] + math.sin(a) * 5),
                                                    (c[0] + math.cos(a + 0.7) * 2, c[1] + math.sin(a + 0.7) * 2)])
        pygame.draw.circle(s, (120, 30, 40), c, 1)
    elif kind == "chicken":
        s = pygame.Surface((16, 11), SRCALPHA)
        pygame.draw.ellipse(s, (196, 110, 50), (0, 1, 12, 10))
        pygame.draw.ellipse(s, (236, 160, 80), (2, 2, 6, 4))
        pygame.draw.line(s, (240, 236, 220), (10, 6), (14, 4), 2)
        pygame.draw.circle(s, (240, 236, 220), (15, 4), 1)
        pygame.draw.circle(s, (240, 236, 220), (14, 2), 1)
    elif kind == "soda":
        s = pygame.Surface((7, 11), SRCALPHA)
        pygame.draw.rect(s, (220, 40, 50), (0, 1, 7, 10))
        pygame.draw.rect(s, (200, 200, 210), (0, 0, 7, 2))
        pygame.draw.line(s, (255, 255, 255), (1, 5), (5, 5))
        pygame.draw.line(s, (255, 140, 140), (1, 2), (1, 9))
    elif kind == "cash":
        s = pygame.Surface((13, 8), SRCALPHA)
        s.fill((80, 160, 90))
        pygame.draw.rect(s, (40, 110, 50), (0, 0, 13, 8), 1)
        pygame.draw.circle(s, (200, 240, 200), (6, 4), 2)
        pygame.draw.line(s, (230, 220, 120), (4, 0), (4, 7), 2)
    elif kind == "plank":
        s = pygame.Surface((7, 4), SRCALPHA)
        s.fill((176, 120, 64) if k % 2 else (130, 84, 44))
    else:
        s = pygame.Surface((8, 8), SRCALPHA)
        s.fill((255, 0, 255))
    out = outlined(s)
    _prop[key] = out
    return out


_glow_cache = {}


def soft_ellipse(w, h, color, alpha):
    key = ("el", w, h, color, alpha)
    s = _glow_cache.get(key)
    if s is None:
        s = pygame.Surface((w, h), SRCALPHA)
        pygame.draw.ellipse(s, (*color, alpha), (0, 0, w, h))
        _glow_cache[key] = s
    return s


def glow(r, color):
    key = (r, color)
    s = _glow_cache.get(key)
    if s is None:
        s = pygame.Surface((r * 2 + 1, r * 2 + 1))
        for i in range(r, 0, -1):
            f = (1 - i / r) ** 1.7
            pygame.draw.circle(s, shade(color, f), (r, r), i)
        _glow_cache[key] = s
    return s


def soft_circle(r, color, alpha):
    key = ("sc", r, color, alpha)
    s = _glow_cache.get(key)
    if s is None:
        s = pygame.Surface((r * 2 + 1, r * 2 + 1), SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (r, r), r)
        _glow_cache[key] = s
    return s


def impact_star(size, color=(255, 255, 220)):
    key = ("star", size, color)
    s = _glow_cache.get(key)
    if s is None:
        s = pygame.Surface((size * 2 + 1,) * 2, SRCALPHA)
        c = size
        pygame.draw.polygon(s, color, [(c, 0), (c + 2, c - 2), (2 * c, c), (c + 2, c + 2), (c, 2 * c),
                                       (c - 2, c + 2), (0, c), (c - 2, c - 2)])
        pygame.draw.circle(s, (255, 255, 255), (c, c), max(2, size // 3))
        _glow_cache[key] = s
    return s


def neon_text(s, color, size=7):
    """Glowing neon sign text: bright core over a soft coloured halo."""
    key = ("neon", s, color)
    img = _glow_cache.get(key)
    if img is None:
        core = bitmap_text(s, lerp(color, (255, 255, 255), 0.55))
        halo = bitmap_text(s, color)
        w, h = core.get_size()
        img = pygame.Surface((w + 6, h + 6), SRCALPHA)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if abs(dx) + abs(dy) <= 3:
                    tmp = halo.copy()
                    tmp.set_alpha(55)
                    img.blit(tmp, (3 + dx, 3 + dy))
        img.blit(halo, (3, 4))
        img.blit(core, (3, 3))
        _glow_cache[key] = img
    return img


# ----------------------------------------------------------------------------
# Backgrounds
# ----------------------------------------------------------------------------
WALL_TOP = 36
TILE_W = 64
SIGNS = ("BAR", "HOTEL", "NOODLES", "24H", "ARCADE", "PAWN", "CLUB", "DINER", "TATTOO", "KARAOKE", "RAMEN",
         "LIQUOR", "VIDEO", "POOL")
NEON_COLS = ((255, 60, 160), (60, 230, 255), (255, 220, 60), (120, 255, 120), (255, 110, 40), (200, 120, 255))


class Background:
    def __init__(self, theme, length, hazards=()):
        self.theme = theme
        self.th = THEMES[theme]
        self.length = length
        self.tiles = {}
        self.signs = {}
        self.water = [(h[1], h[2]) for h in hazards if h[0] == "water"]
        self.sky = pygame.Surface((W, FLOOR_Y - HUD_H))
        dither_fill(self.sky, self.sky.get_rect(), *self.th["sky"], steps=10)
        rnd = random.Random(hash(theme) & 0xffff)
        if theme in ("neon", "tower", "docks"):
            for _ in range(40):
                self.sky.set_at((rnd.randrange(W), rnd.randrange(60)), (200, 200, 240))
        self.far = self._far(rnd)
        self.floor = self._floor_tile()

    # --- far layer -------------------------------------------------------
    def _far(self, rnd):
        fw = W * 2
        surf = pygame.Surface((fw, FLOOR_Y - HUD_H), SRCALPHA)
        h = surf.get_height()
        th = self.theme
        col, win = self.th["far"], self.th["win"]
        if th == "docks":
            sea_y = h - 34
            pygame.draw.circle(surf, (255, 190, 110), (fw // 3, sea_y), 18)
            surf.fill((40, 50, 90), (0, sea_y, fw, h - sea_y))
            for y in range(sea_y + 2, h, 3):
                for x in range(rnd.randrange(8), fw, rnd.randint(12, 26)):
                    pygame.draw.line(surf, (230, 140, 100) if y < sea_y + 12 else (80, 100, 150), (x, y), (x + 5, y))
            for cx in range(40, fw, 150):          # cranes
                base = sea_y
                ht = rnd.randint(50, 70)
                pygame.draw.line(surf, col, (cx, base), (cx, base - ht), 3)
                pygame.draw.line(surf, col, (cx - 20, base - ht), (cx + 46, base - ht + 6), 2)
                pygame.draw.line(surf, col, (cx, base - ht - 8), (cx + 40, base - ht + 6), 1)
                pygame.draw.line(surf, col, (cx + 36, base - ht + 6), (cx + 36, base - ht + 24), 1)
            ship_x = fw // 2 + 40
            pygame.draw.polygon(surf, col, [(ship_x, sea_y), (ship_x + 120, sea_y), (ship_x + 130, sea_y - 12),
                                            (ship_x - 6, sea_y - 12)])
            surf.fill(col, (ship_x + 80, sea_y - 26, 24, 14))
            return surf
        if th == "factory":
            surf.fill((0, 0, 0, 0))
            for cx in range(0, fw, 90):
                ht = rnd.randint(50, 90)
                surf.fill(col, (cx + 10, h - ht, 18, ht))
                pygame.draw.rect(surf, shade(col, 1.3), (cx + 10, h - ht, 18, 4))
                bw = rnd.randint(40, 60)
                surf.fill(shade(col, 0.85), (cx + 30, h - ht // 2, bw, ht // 2))
                for k in range(3):
                    pygame.draw.circle(surf, (255, 120, 40), (cx + 38 + k * 12, h - ht // 2 + 10), 2)
            return surf
        # city skylines
        x = 0
        while x < fw:
            bw = rnd.randint(18, 40)
            bh = rnd.randint(30, h - 10)
            c = shade(col, rnd.uniform(0.8, 1.2))
            surf.fill(c, (x, h - bh, bw, bh))
            if rnd.random() < 0.3:
                pygame.draw.line(surf, c, (x + bw // 2, h - bh), (x + bw // 2, h - bh - 10))
                surf.set_at((x + bw // 2, h - bh - 11), (255, 60, 60))
            for wy in range(h - bh + 4, h - 4, 5):
                for wx in range(x + 3, x + bw - 3, 4):
                    if rnd.random() < 0.35:
                        surf.fill(shade(win, rnd.uniform(0.6, 1.0)), (wx, wy, 2, 2))
            x += bw + rnd.randint(-4, 4)
        if th == "neon":
            pygame.draw.circle(surf, (250, 240, 210), (fw // 4, 22), 10)
            pygame.draw.circle(surf, (210, 200, 180), (fw // 4 + 3, 20), 2)
        return surf

    # --- mid layer tiles --------------------------------------------------
    def _tile(self, i):
        t = self.tiles.get(i)
        if t is not None:
            return t
        rnd = random.Random(i * 7919 + hash(self.theme) % 1000)
        th = self.theme
        hgt = FLOOR_Y - WALL_TOP
        s = pygame.Surface((TILE_W, hgt), SRCALPHA)
        signs = []
        if th == "neon":
            bld = i // 2
            br = random.Random(bld * 31 + 5)
            roof = br.choice((0, 6, 14, 22))
            wall = br.choice(((120, 50, 48), (96, 60, 70), (70, 70, 96), (110, 84, 60), (60, 80, 84)))
            s.fill(wall, (0, roof, TILE_W, hgt - roof))
            for y in range(roof + 4, hgt, 4):           # bricks
                off = 0 if (y // 4) % 2 else 4
                pygame.draw.line(s, shade(wall, 0.82), (0, y), (TILE_W, y))
                for x in range(off, TILE_W, 8):
                    s.set_at((x, y - 2), shade(wall, 0.82))
            pygame.draw.rect(s, shade(wall, 1.3), (0, roof, TILE_W, 3))
            for wx in (8, 36):                          # upper windows
                lit = rnd.random() < 0.5
                c = (255, 214, 120) if lit else (30, 30, 50)
                s.fill(shade(wall, 0.5), (wx - 1, roof + 10, 20, 22))
                s.fill(c, (wx, roof + 11, 18, 20))
                if lit:
                    pygame.draw.line(s, (200, 150, 80), (wx, roof + 21), (wx + 17, roof + 21))
                    s.fill((150, 90, 60), (wx, roof + 11, 18, 5))
                pygame.draw.line(s, shade(wall, 1.2), (wx - 1, roof + 32), (wx + 19, roof + 32))
            if rnd.random() < 0.35:                     # fire escape
                fy = roof + 34
                pygame.draw.rect(s, (24, 20, 26), (4, fy, 56, 2))
                for x in range(4, 60, 4):
                    pygame.draw.line(s, (24, 20, 26), (x, fy - 6), (x, fy))
                pygame.draw.line(s, (24, 20, 26), (4, fy - 6), (60, fy - 6))
                pygame.draw.line(s, (24, 20, 26), (12, fy), (40, hgt - 46), 2)
            gf = hgt - 44                               # ground floor shop
            kind = rnd.choice(("shop", "shop", "shutter", "door"))
            s.fill((40, 36, 44), (0, gf, TILE_W, 44))
            if kind == "shop":
                s.fill((255, 200, 120), (4, gf + 12, 40, 26))
                s.fill((230, 150, 90), (4, gf + 30, 40, 8))
                for x in range(6, 44, 6):
                    pygame.draw.line(s, (250, 230, 180), (x, gf + 13), (x - 2, gf + 28))
                s.fill((70, 50, 40), (48, gf + 10, 12, 34))
                s.fill((255, 230, 150), (52, gf + 22, 2, 2))
                aw = rnd.choice(NEON_COLS)
                for x in range(0, TILE_W, 8):
                    s.fill(aw if (x // 8) % 2 else (240, 240, 240), (x, gf + 2, 8, 6))
                pygame.draw.line(s, shade(aw, 0.6), (0, gf + 8), (TILE_W, gf + 8))
            elif kind == "shutter":
                s.fill((120, 124, 130), (6, gf + 6, 52, 38))
                for y in range(gf + 8, gf + 44, 3):
                    pygame.draw.line(s, (90, 94, 100), (6, y), (57, y))
                for k in range(rnd.randint(2, 4)):     # graffiti blobs
                    c = rnd.choice(NEON_COLS)
                    pygame.draw.ellipse(s, shade(c, 0.8), (rnd.randint(8, 40), rnd.randint(gf + 14, gf + 32), 14, 7), 2)
            else:
                s.fill((60, 40, 34), (22, gf + 6, 20, 38))
                pygame.draw.rect(s, (30, 20, 18), (22, gf + 6, 20, 38), 1)
                s.fill((255, 240, 180), (24, gf + 2, 16, 3))
                s.fill((240, 200, 90), (38, gf + 26, 2, 2))
            if rnd.random() < 0.55:
                word = rnd.choice(SIGNS)
                c = rnd.choice(NEON_COLS)
                signs.append((neon_text(word, c), (rnd.randint(2, max(3, TILE_W - 6 * len(word) - 4)),
                                                   gf - 12), rnd.random() < 0.25))
        elif th == "docks":
            bld = i // 3
            br = random.Random(bld * 17 + 3)
            if br.random() < 0.45:                      # warehouse wall
                roof = 18
                c = br.choice(((120, 110, 100), (90, 100, 110), (130, 96, 70)))
                s.fill(c, (0, roof, TILE_W, hgt - roof))
                for x in range(0, TILE_W, 4):
                    pygame.draw.line(s, shade(c, 0.85), (x, roof), (x, hgt))
                pygame.draw.rect(s, shade(c, 0.6), (0, roof, TILE_W, 4))
                if i % 3 == 1:
                    s.fill((50, 50, 54), (8, hgt - 60, 48, 60))
                    for y in range(hgt - 58, hgt, 4):
                        pygame.draw.line(s, (70, 70, 76), (8, y), (55, y))
                    text(s, str(br.randint(1, 9)), 16, (32, roof + 16), (240, 230, 200), shadow=None)
                pygame.draw.circle(s, (255, 230, 160), (32, roof + 8), 3)
            else:                                       # stacked containers
                rows = br.randint(2, 4)
                for r in range(rows):
                    c = br.choice(((180, 60, 40), (40, 100, 160), (60, 140, 80), (200, 150, 40), (120, 70, 140)))
                    y0 = hgt - (r + 1) * 22
                    off = (i * 13 + r * 29) % 24
                    s.fill(c, (0, y0, TILE_W, 21))
                    for x in range(-off, TILE_W, 4):
                        pygame.draw.line(s, shade(c, 0.75), (x, y0 + 2), (x, y0 + 19))
                    pygame.draw.line(s, shade(c, 1.3), (0, y0), (TILE_W, y0))
                    pygame.draw.line(s, shade(c, 0.5), (0, y0 + 20), (TILE_W, y0 + 20))
                    if (i + r) % 3 == 0:
                        pygame.draw.line(s, shade(c, 0.45), (TILE_W - 1, y0), (TILE_W - 1, y0 + 20), 2)
            pygame.draw.line(s, (60, 50, 40), (0, hgt - 1), (TILE_W, hgt - 1), 2)
        elif th == "factory":
            c = (70, 66, 72)
            s.fill(c)
            for y in range(0, hgt, 24):
                pygame.draw.line(s, shade(c, 0.7), (0, y), (TILE_W, y))
                for x in range(2, TILE_W, 12):
                    s.set_at((x, y + 3), shade(c, 1.4))
            pygame.draw.line(s, shade(c, 0.7), (TILE_W - 1, 0), (TILE_W - 1, hgt))
            py = 20 + (i % 3) * 6
            pygame.draw.rect(s, (110, 96, 70), (0, py, TILE_W, 7))
            pygame.draw.line(s, (170, 150, 110), (0, py + 1), (TILE_W, py + 1))
            pygame.draw.rect(s, (90, 110, 120), (0, py + 30, TILE_W, 5))
            pygame.draw.line(s, (150, 170, 180), (0, py + 31), (TILE_W, py + 31))
            if i % 4 == 0:
                pygame.draw.rect(s, (60, 70, 76), (10, py + 26, 8, 12))
            kind = rnd.choice(("furnace", "gauge", "plain", "stripes"))
            if kind == "furnace":
                s.fill((30, 24, 24), (12, hgt - 44, 40, 34))
                for y in range(hgt - 42, hgt - 12):
                    t = (y - (hgt - 42)) / 30
                    pygame.draw.line(s, lerp((255, 220, 120), (200, 50, 20), t), (14, y), (49, y))
                for x in range(14, 50, 6):
                    pygame.draw.line(s, (40, 30, 30), (x, hgt - 42), (x, hgt - 13), 2)
            elif kind == "gauge":
                pygame.draw.circle(s, (220, 220, 210), (32, hgt - 40), 8)
                pygame.draw.circle(s, (40, 40, 40), (32, hgt - 40), 8, 1)
                pygame.draw.line(s, (200, 30, 30), (32, hgt - 40), (37, hgt - 45))
            elif kind == "stripes":
                for x in range(-10, TILE_W, 10):
                    pygame.draw.polygon(s, (230, 190, 40), [(x, hgt - 12), (x + 5, hgt - 12), (x + 10, hgt - 20),
                                                           (x + 5, hgt - 20)])
                s.fill((30, 30, 30), (0, hgt - 22, TILE_W, 2))
            s.fill((40, 38, 44), (0, hgt - 8, TILE_W, 8))
        else:   # tower
            c = (120, 24, 30)
            s.fill(c)
            win = i % 3 == 1
            if win:                                      # window: see the far city through it
                s.fill((0, 0, 0, 0), (8, 16, 48, 60))
                pygame.draw.rect(s, (200, 160, 70), (7, 15, 50, 62), 2)
                pygame.draw.line(s, (200, 160, 70), (32, 16), (32, 76), 2)
                pygame.draw.line(s, (200, 160, 70), (8, 46), (56, 46), 1)
            else:
                pygame.draw.rect(s, shade(c, 0.75), (6, 12, 52, 70), 2)
                if i % 3 == 2:                           # serpent banner
                    s.fill((30, 20, 24), (18, 10, 28, 60))
                    pygame.draw.polygon(s, (30, 20, 24), [(18, 70), (46, 70), (32, 80)])
                    pts = [(32 + math.sin(k * 0.55) * 7, 18 + k * 3.2) for k in range(16)]
                    pygame.draw.lines(s, (230, 190, 70), False, pts, 3)
                    pygame.draw.circle(s, (230, 190, 70), (int(pts[0][0]), int(pts[0][1])), 3)
                    s.set_at((int(pts[0][0]) + 1, int(pts[0][1]) - 1), (200, 30, 30))
                else:
                    for k in range(3):
                        pygame.draw.circle(s, (230, 190, 70), (32, 26 + k * 20), 4, 1)
            s.fill((60, 14, 18), (0, 0, TILE_W, 8))
            pygame.draw.line(s, (220, 180, 80), (0, 8), (TILE_W, 8))
            s.fill((60, 14, 18), (0, hgt - 16, TILE_W, 16))
            pygame.draw.line(s, (220, 180, 80), (0, hgt - 16), (TILE_W, hgt - 16))
            pygame.draw.line(s, (40, 10, 14), (0, 0), (0, hgt), 2)
            if i % 2 == 0:                               # lantern
                pygame.draw.line(s, (40, 20, 20), (62, 8), (62, 22))
                pygame.draw.ellipse(s, (255, 120, 60), (57, 22, 10, 13))
                pygame.draw.ellipse(s, (255, 210, 140), (59, 25, 6, 7))
        self.tiles[i] = s
        self.signs[i] = signs
        return s

    def _floor_tile(self):
        th = self.theme
        fh = H - FLOOR_Y
        s = pygame.Surface((TILE_W, fh))
        rnd = random.Random(99)
        if th == "neon":
            s.fill((112, 108, 120))
            for y in (0, 10, 20):
                pygame.draw.line(s, (86, 82, 96), (0, y), (TILE_W, y))
            for x in range(0, TILE_W, 16):
                pygame.draw.line(s, (86, 82, 96), (x, 0), (x, 22))
            s.fill((150, 146, 156), (0, 22, TILE_W, 2))
            s.fill((60, 60, 70), (0, 24, TILE_W, 2))
            s.fill((46, 44, 56), (0, 26, TILE_W, fh - 26))
            for _ in range(60):
                s.set_at((rnd.randrange(TILE_W), rnd.randrange(26, fh)), (64, 62, 74))
            s.fill((220, 190, 60), (8, 50, 24, 2))
        elif th == "docks":
            s.fill((128, 92, 62))
            for y in range(0, fh, 6):
                pygame.draw.line(s, (90, 62, 42), (0, y), (TILE_W, y))
                pygame.draw.line(s, (150, 112, 80), (0, y + 1), (TILE_W, y + 1))
                off = (y * 7) % TILE_W
                pygame.draw.line(s, (90, 62, 42), (off, y), (off, y + 5))
                s.set_at(((off + 30) % TILE_W, y + 3), (60, 40, 30))
        elif th == "factory":
            s.fill((84, 84, 92))
            for y in range(0, fh, 16):
                pygame.draw.line(s, (54, 54, 62), (0, y), (TILE_W, y))
            for y in range(3, fh, 5):
                for x in range((y // 5 % 2) * 3, TILE_W, 6):
                    s.set_at((x, y), (110, 110, 120))
        else:
            for row in range(0, fh, 8):
                for x in range(0, TILE_W, 16):
                    c = (180, 170, 160) if ((x // 16) + row // 8) % 2 else (40, 30, 34)
                    s.fill(c, (x, row, 16, 8))
            s.fill((90, 20, 26), (0, 0, TILE_W, 4))
        return s

    # --- drawing ---------------------------------------------------------
    def draw(self, surf, camx, t):
        surf.blit(self.sky, (0, HUD_H))
        fw = self.far.get_width()
        off = int(camx * 0.3) % fw
        surf.blit(self.far, (-off, HUD_H))
        surf.blit(self.far, (fw - off, HUD_H))
        cam = int(camx)
        first = cam // TILE_W
        for i in range(first, first + W // TILE_W + 2):
            sx = i * TILE_W - cam
            surf.blit(self._tile(i), (sx, WALL_TOP))
            for img, (ox, oy), flick in self.signs.get(i, ()):
                if flick and (int(t * 7 + i) % 11 == 0 or int(t * 13 + i * 3) % 23 == 0):
                    continue
                surf.blit(img, (sx + ox, WALL_TOP + oy))
        fo = cam % TILE_W
        for x in range(-fo, W, TILE_W):
            surf.blit(self.floor, (x, FLOOR_Y))
        # perspective seams
        seam = {"neon": (70, 68, 82), "docks": (96, 66, 44), "factory": (60, 60, 68), "tower": (70, 50, 54)}[self.theme]
        step = 32
        for wx in range((cam // step) * step, cam + W + step, step):
            sx = wx - cam
            bx = sx + (sx - W / 2) * 0.55
            if self.theme == "neon":
                pygame.draw.line(surf, seam, (sx, FLOOR_Y + 26), (sx + (sx - W / 2) * 0.12 * 1.6, H), 1) \
                    if wx % 64 == 0 else None
            else:
                pygame.draw.line(surf, seam, (sx, FLOOR_Y), (bx, H), 1)
        pygame.draw.line(surf, (20, 16, 22), (0, FLOOR_Y), (W, FLOOR_Y))
        if self.theme == "docks":
            self._draw_water(surf, cam, t)

    def _draw_water(self, surf, cam, t):
        y0 = H - 8
        surf.fill((30, 50, 90), (0, y0, W, H - y0))
        for x0, x1 in self.water:
            a, b = x0 - cam, x1 - cam
            if b < 0 or a > W:
                continue
            top = FLOOR_Y + 51
            surf.fill((30, 50, 90), (a, top, b - a, H - top))
            pygame.draw.line(surf, (70, 46, 30), (a, top), (b, top), 2)
            for y in range(top + 4, H, 4):
                for x in range(int(a) + int(t * 20 + y * 3) % 12, int(b), 12):
                    pygame.draw.line(surf, (80, 120, 170), (x, y), (x + 4, y))
            surf.fill((70, 46, 30), (a - 2, top, 3, H - top))
            surf.fill((70, 46, 30), (b - 1, top, 3, H - top))
        for x in range(-(cam % 48), W, 48):
            surf.fill((60, 40, 28), (x, y0 - 2, 4, 10))
        for x in range(int(t * 14) % 10, W, 10):
            pygame.draw.line(surf, (80, 120, 170), (x, y0 + 4), (x + 4, y0 + 4))


def draw_vent(surf, sx, sy, state):
    """Steam vent grate on the floor. state: 0 idle, 1 warning, 2 venting."""
    pygame.draw.ellipse(surf, (30, 30, 34), (sx - 13, sy - 4, 26, 8))
    for k in range(-9, 10, 4):
        pygame.draw.line(surf, (90, 90, 96), (sx + k, sy - 3), (sx + k, sy + 3))
    c = (230, 190, 40) if state else (160, 140, 40)
    pygame.draw.ellipse(surf, c, (sx - 15, sy - 5, 30, 10), 1)


# ----------------------------------------------------------------------------
# HUD
# ----------------------------------------------------------------------------
def energy_bar(surf, x, y, w, h, frac, col, back=(40, 20, 30), segs=None):
    surf.fill((10, 8, 14), (x - 1, y - 1, w + 2, h + 2))
    surf.fill(back, (x, y, w, h))
    fw = int(w * max(0.0, min(1.0, frac)))
    if fw > 0:
        surf.fill(col, (x, y, fw, h))
        surf.fill(lerp(col, (255, 255, 255), 0.45), (x, y, fw, 1))
        surf.fill(shade(col, 0.65), (x, y + h - 1, fw, 1))
    if segs:
        for k in range(1, segs):
            sx = x + k * w // segs
            surf.fill((10, 8, 14), (sx, y, 1, h))


def hud_back():
    s = pygame.Surface((W, HUD_H))
    dither_fill(s, s.get_rect(), (24, 16, 40), (8, 6, 14), steps=6)
    pygame.draw.line(s, (120, 60, 160), (0, HUD_H - 1), (W, HUD_H - 1))
    pygame.draw.line(s, (60, 30, 90), (0, HUD_H - 2), (W, HUD_H - 2))
    return s


def go_arrow(surf, t):
    if int(t * 3) % 2:
        return
    x, y = W - 46, 80
    text(surf, "GO", 13, (x, y), (255, 230, 90), outline=True)
    pygame.draw.polygon(surf, (16, 10, 20), [(x + 9, y - 7), (x + 22, y), (x + 9, y + 7)])
    pygame.draw.polygon(surf, (255, 230, 90), [(x + 10, y - 5), (x + 20, y), (x + 10, y + 5)])
