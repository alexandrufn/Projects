"""Procedural 16-bit style graphics: pose-driven fighters, temple backgrounds, effects, UI.

Fighters are drawn from a handful of joint targets (hip, chest, head, hands, feet) with two-bone
IK for arms and legs, so any pose can be animated for any character and any body scale.
"""
import math
import random

import pygame

from config import W, H, GROUND, HUD_H, BGS
from textgfx import lerp, shade, text, fancy_text, wrap, font, text_width, dither_fill, BAYER  # noqa: F401

SRCALPHA = pygame.SRCALPHA
OUT = (20, 10, 16)
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
        return _pose((0, -22), (0, -35 + b * 0.8), (1, -42 + b * 0.8), (9, -29 + b * 0.6), (4, -26), (6, 0), (-6, 0))
    if name in ("walk", "run"):
        a = ph * math.tau
        amp, lift, lean = (9, 5, 0) if name == "walk" else (11, 8, 5)
        sw = math.sin(a) * amp
        lf, lb = max(0, math.cos(a)) * lift, max(0, -math.cos(a)) * lift
        bob = -abs(math.sin(a)) * 1.3
        return _pose((lean * 0.4, -22 + bob), (1 + lean, -35 + bob), (2 + lean * 1.4, -42 + bob),
                     (9 + lean, -29 + math.sin(a) * 2), (4 - lean, -26 - math.sin(a) * 2), (sw, -lf), (-sw, -lb))
    if name == "staff_walk":
        d = make_pose("walk", ph)
        d["staff"] = ((-6, -2), (-6, -62))
        return d
    if name == "crouch":
        return _pose((-1, -12), (3, -23), (5, -30), (10, -19), (5, -15), (9, 0), (-7, 0))
    if name == "jump":
        return _pose((0, -20), (0, -33), (1, -40), (11, -33), (5, -35), (8, -9 + b * 0), (-3, -4))
    if name == "punch_w":
        return _pose((0, -22), (-1, -35), (0, -42), (2, -30), (8, -31), (8, 0), (-8, 0))
    if name == "punch":
        return _pose((0, -22), (5, -35), (7, -42), (23, -33), (-3, -27), (10, 0), (-8, 0))
    if name == "kick_w":
        return _pose((0, -22), (-3, -35), (-3, -42), (8, -33), (-3, -33), (8, -24), (-5, 0))
    if name == "kick":
        return _pose((1, -22), (-4, -35), (-4, -42), (8, -37), (-10, -33), (24, -33), (-5, 0))
    if name == "cpunch":
        return _pose((-1, -12), (5, -22), (7, -29), (23, -17), (3, -16), (9, 0), (-7, 0))
    if name == "ckick_w":
        return _pose((-1, -12), (1, -23), (3, -30), (9, -22), (3, -20), (5, -9), (-8, 0))
    if name == "ckick":
        return _pose((3, -11), (0, -21), (1, -28), (9, -22), (-5, -17), (26, -3), (-9, 0))
    if name == "jkick":
        return _pose((0, -21), (-4, -33), (-4, -40), (6, -36), (-9, -34), (22, -24), (-6, -10))
    if name == "hurt":
        return _pose((-1, -22), (-5, -34), (-8, -40), (3, -40), (-7, -38), (4, 0), (-9, 0))
    if name == "dead":
        return _pose((-9, -6), (-22, -7), (-31, -6), (-24, -13), (-30, -3), (8, -3), (5, -9))
    if name == "grab":
        return _pose((0, -22), (2, -35), (3, -42), (16, -33), (14, -29), (6, 0), (-6, 0))
    if name == "gripped":
        return _pose((-1, -22), (-3, -34), (-4, -40), (4, -30), (-6, -30), (5, 0), (-7, 0))
    if name == "throw_hi":
        return _pose((0, -22), (-2, -35), (-2, -42), (6, -50), (-4, -27), (7, 0), (-7, 0))
    if name == "throw_lo":
        return _pose((0, -19), (3, -30), (5, -37), (12, -17), (-4, -26), (9, 0), (-7, 0))
    if name == "throw":
        return _pose((0, -22), (4, -35), (6, -42), (19, -34), (-3, -27), (8, 0), (-7, 0))
    if name == "stun":
        return _pose((-1, -22), (-3, -33), (1, -37), (3, -21), (-4, -21), (6, 0), (-6, 0))
    if name == "block":
        return _pose((-1, -21), (-1, -34), (0, -41), (10, -35), (8, -31), (6, 0), (-6, 0))
    if name == "victory":
        return _pose((0, -22), (0, -35), (1, -42), (8, -52), (-6, -52), (7, 0), (-7, 0))
    if name == "bow":
        return _pose((-2, -21), (6, -31), (12, -35), (3, -24), (0, -23), (6, 0), (-6, 0))
    if name == "cast":
        return _pose((0, -22), (1, -35), (2, -42), (18, -35), (14, -38), (6, 0), (-7, 0))
    if name == "cast_hi":
        return _pose((0, -22), (-1, -35), (0, -42), (15, -48), (11, -50), (6, 0), (-7, 0))
    if name == "cast_lo":
        return _pose((0, -17), (4, -28), (6, -35), (15, -15), (11, -17), (10, 0), (-8, 0))
    if name == "slam_w":
        return _pose((0, -22), (-3, -35), (-3, -42), (4, -52), (0, -52), (6, 0), (-6, 0))
    if name == "slam":
        return _pose((2, -15), (8, -26), (11, -32), (15, -9), (11, -7), (10, 0), (-8, 0))
    if name == "stomp_w":
        return _pose((0, -22), (-3, -35), (-3, -42), (3, -50), (-1, -50), (8, -26), (-5, 0))
    if name == "dash":
        return _pose((2, -20), (10, -31), (15, -36), (26, -31), (2, -24), (9, -4), (-13, -3))
    if name == "dash_w":
        return _pose((-1, -19), (-4, -31), (-4, -38), (-2, -26), (5, -29), (8, 0), (-10, 0))
    if name == "burst_w":
        return _pose((0, -22), (0, -36), (1, -43), (12, -46), (-9, -45), (7, 0), (-7, 0), aura=1)
    if name == "burst":
        return _pose((0, -22), (0, -35), (1, -42), (16, -38), (-14, -38), (9, 0), (-9, 0), aura=2)
    if name == "flame_w":
        return _pose((0, -22), (-4, -35), (-6, -43), (6, -28), (0, -27), (7, 0), (-7, 0))
    if name == "flame":
        return _pose((0, -22), (4, -35), (9, -41), (8, -30), (0, -28), (8, 0), (-8, 0))
    if name == "staff_hi_w":
        return _pose((0, -22), (-2, -35), (-2, -42), (6, -38), (-1, -34), (6, 0), (-6, 0),
                     staff=((-12, -22), (30, -62)))
    if name == "staff_lo_w":
        return _pose((-1, -14), (0, -25), (2, -32), (6, -20), (-1, -17), (9, 0), (-8, 0),
                     staff=((-22, -26), (26, -2)))
    if name == "staff_hi":
        return _pose((0, -22), (4, -35), (6, -42), (19, -36), (8, -33), (10, 0), (-8, 0),
                     staff=((-16, -34), (58, -38)))
    if name == "staff_lo":
        return _pose((2, -13), (6, -24), (8, -31), (19, -12), (8, -11), (10, 0), (-8, 0),
                     staff=((-16, -12), (60, -5)))
    if name == "staff_idle":
        return _pose((0, -22), (0, -35 + b * 0.8), (1, -42 + b * 0.8), (8, -26), (3, -30), (6, 0), (-6, 0),
                     staff=((-6, -2), (-6, -62)))
    if name == "spin":
        ang = ph * math.tau
        c, s = math.cos(ang), math.sin(ang)
        return _pose((0, -16), (1, -28), (2, -35), (8, -26), (3, -25), (9, 0), (-9, 0),
                     staff=((-c * 44, -26 - s * 12), (c * 44, -26 + s * 12)))
    if name == "blade_w":
        return _pose((-1, -21), (-4, -34), (-4, -41), (-3, -32), (-8, -30), (8, 0), (-9, 0), bdir=(-0.9, -0.4))
    if name == "blade":
        return _pose((1, -21), (5, -34), (7, -41), (20, -32), (-4, -28), (10, 0), (-9, 0), bdir=(1.0, -0.15))
    if name == "blade_up":
        return _pose((0, -22), (0, -35), (1, -42), (10, -50), (6, -49), (6, 0), (-6, 0), bdir=(0.6, -0.8))
    if name == "dive":
        return _pose((2, -20), (6, -30), (9, -35), (16, -22), (10, -24), (6, -9), (-6, -14), bdir=(0.9, 0.5))
    raise KeyError(name)


# Pre-quantised animation phases
PHASES = {"idle": 4, "walk": 8, "run": 8, "spin": 8, "staff_walk": 8, "staff_idle": 4}


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


def draw_figure(pose, pal, ex, s):
    CW, CH = int(150 * s), int(112 * s)
    AX, AY = int(75 * s), int(98 * s)
    surf = pygame.Surface((CW, CH), SRCALPHA)

    def P(p):
        return (AX + p[0] * s, AY + p[1] * s)

    def Wd(w):
        return max(1, int(round(w * s)))

    hip, chest, head = P(pose["hip"]), P(pose["chest"]), P(pose["head"])
    skin, gi, pants = pal["skin"], pal["gi"], pal["pants"]
    gi_d, pants_d, skin_d = shade(gi, 0.72), shade(pants, 0.72), shade(skin, 0.78)
    robe = pal["robe"] if "robe" in ex else None
    bare = pal["bare"]
    sh_f = (chest[0] + 1 * s, chest[1] + 2 * s)
    sh_b = (chest[0] - 1 * s, chest[1] + 2 * s)
    knee_f, foot_f = ik((hip[0] + 2 * s, hip[1]), P(pose["ff"]), THIGH * s, SHIN * s, -1)
    knee_b, foot_b = ik((hip[0] - 2 * s, hip[1]), P(pose["fb"]), THIGH * s, SHIN * s, -1)
    el_f, hand_f = ik(sh_f, P(pose["hf"]), UARM * s, FARM * s, 1)
    el_b, hand_b = ik(sh_b, P(pose["hb"]), UARM * s, FARM * s, 1)

    if pose.get("aura"):
        r = (22 if pose["aura"] == 1 else 34) * s
        for k, a in ((1.0, 40), (0.7, 60), (0.45, 80)):
            circ = pygame.Surface((int(r * 2 * k) + 2,) * 2, SRCALPHA)
            pygame.draw.circle(circ, (255, 150, 60, a), (circ.get_width() // 2,) * 2, int(r * k))
            surf.blit(circ, circ.get_rect(center=(int(chest[0]), int(chest[1] + 4 * s))))

    if "cape" in ex:
        c = pal["cape"] or (150, 24, 40)
        fl = math.sin(pose["chest"][0] * 0.3) * 1.5
        pts = [(chest[0] - 3 * s, chest[1]), (chest[0] + 1 * s, chest[1]),
               (hip[0] - 14 * s, AY - (6 + fl) * s), (hip[0] - 7 * s, AY - 1 * s), (hip[0] - 18 * s, AY - 4 * s)]
        pygame.draw.polygon(surf, shade(c, 0.8), pts)
        pygame.draw.polygon(surf, c, [pts[0], pts[1], pts[2], pts[3]])
        pygame.draw.line(surf, shade(c, 1.35), pts[0], pts[2], 1)

    # back arm / back leg
    sleeve_b = skin_d if bare else gi_d
    _limb(surf, [sh_b, el_b], Wd(3.4), sleeve_b)
    _limb(surf, [el_b, hand_b], Wd(3.0), skin_d)
    pygame.draw.circle(surf, skin_d, (int(hand_b[0]), int(hand_b[1])), Wd(2.2))
    if not robe:
        _limb(surf, [(hip[0] - 2 * s, hip[1]), knee_b, foot_b], Wd(4.2), pants_d)
    shoe = pal["shoe"]
    for f, col in ((foot_b, shade(shoe, 0.8)),):
        pygame.draw.rect(surf, col, (int(f[0] - 2 * s), int(f[1] - 3 * s), Wd(7), Wd(3.4)))

    # torso
    tp = [(chest[0] - 4 * s, chest[1] - 1 * s), (chest[0] + 4.5 * s, chest[1] - 1 * s),
          (hip[0] + 3.5 * s, hip[1]), (hip[0] - 3.5 * s, hip[1])]
    if robe:
        rp = [(chest[0] - 5 * s, chest[1] - 1 * s), (chest[0] + 5 * s, chest[1] - 1 * s),
              (hip[0] + 9 * s, AY - 2 * s), (hip[0] - 9 * s, AY - 2 * s)]
        pygame.draw.polygon(surf, robe, rp)
        pygame.draw.line(surf, shade(robe, 1.3), rp[0], rp[3], 1)
        pygame.draw.line(surf, shade(robe, 0.7), rp[1], rp[2], 1)
        pygame.draw.line(surf, shade(robe, 0.75), (hip[0], hip[1] + 2 * s), (hip[0] + 1 * s, AY - 2 * s), 1)
        for k in range(3):
            pygame.draw.line(surf, pal["belt"], (hip[0] - 9 * s, AY - (3 + k * 3) * s),
                             (hip[0] + 9 * s, AY - (3 + k * 3) * s), 1) if k == 0 else None
        for f in (foot_f, foot_b):
            pygame.draw.rect(surf, pal["shoe"], (int(f[0] - 2 * s), int(f[1] - 2 * s), Wd(6), Wd(2.6)))
    else:
        pygame.draw.polygon(surf, skin if bare else gi, tp)
        if bare:
            mid = ((tp[0][0] + tp[1][0]) / 2, (tp[0][1] + tp[2][1]) / 2)
            pygame.draw.line(surf, skin_d, (mid[0] + 1 * s, tp[0][1] + 2 * s), (hip[0] + 1 * s, hip[1] - 2 * s), 1)
            pygame.draw.line(surf, shade(skin, 1.15), (tp[0][0] + 1 * s, tp[0][1] + 1 * s), (tp[0][0] + 1.5 * s,
                                                                                        hip[1] - 3 * s), 1)
            pygame.draw.line(surf, skin_d, (chest[0] - 1 * s, chest[1] + 3 * s), (chest[0] + 3 * s, chest[1] + 3 * s), 1)
        else:
            pygame.draw.line(surf, shade(gi, 1.25), tp[0], (tp[3][0], tp[3][1]), 1)
            pygame.draw.line(surf, gi_d, tp[1], tp[2], 1)
            pygame.draw.line(surf, skin, (chest[0] + 1.5 * s, chest[1] - 1 * s), (hip[0] + 0.5 * s, hip[1] - 3 * s), 1)
            pygame.draw.line(surf, shade(gi, 0.85), (chest[0] + 1 * s, chest[1] - 1 * s), (hip[0], hip[1] - 3 * s), 1)
        by = hip[1] - 2 * s
        pygame.draw.rect(surf, pal["belt"], (int(hip[0] - 4 * s), int(by), Wd(8.5), Wd(2.6)))
        pygame.draw.line(surf, shade(pal["belt"], 1.3), (hip[0] - 4 * s, by), (hip[0] + 4 * s, by), 1)
        pygame.draw.line(surf, pal["belt"], (hip[0] - 4 * s, by + 1 * s), (hip[0] - 8 * s, by + 5 * s), Wd(2))
        pygame.draw.line(surf, shade(pal["belt"], 0.75), (hip[0] - 3 * s, by + 1 * s), (hip[0] - 6 * s, by + 6 * s), Wd(1.5))
        _limb(surf, [(hip[0] + 2 * s, hip[1]), knee_f, foot_f], Wd(4.6), pants, shade(pants, 1.25))
        pygame.draw.rect(surf, pal["shoe"], (int(foot_f[0] - 2 * s), int(foot_f[1] - 3 * s), Wd(7.5), Wd(3.6)))
        pygame.draw.line(surf, shade(pal["shoe"], 1.5), (foot_f[0] - 1 * s, foot_f[1] - 3 * s),
                         (foot_f[0] + 5 * s, foot_f[1] - 3 * s), 1)

    if "pads" in ex:
        for sp, c in ((sh_b, shade(pal["belt"], 0.8)), (sh_f, pal["belt"])):
            pygame.draw.circle(surf, c, (int(sp[0]), int(sp[1] - 1 * s)), Wd(3.8))
            pygame.draw.circle(surf, shade(c, 1.4), (int(sp[0] - 1 * s), int(sp[1] - 2 * s)), max(1, Wd(1.4)))

    # head
    hr = Wd(5.2) if "brow" not in ex else Wd(4.4)
    pygame.draw.circle(surf, skin, (int(head[0]), int(head[1])), hr)
    pygame.draw.circle(surf, skin_d, (int(head[0] - 2 * s), int(head[1] + 1 * s)), max(1, hr - 2), 1)
    pygame.draw.rect(surf, skin, (int(head[0] + 3.5 * s), int(head[1] + 0 * s), Wd(2.2), Wd(2.2)))   # nose
    pygame.draw.rect(surf, skin, (int(head[0] - 1.5 * s), int(head[1] + hr - 1), Wd(4), Wd(3)))        # neck
    if "bald" not in ex and "hat" not in ex:
        pygame.draw.circle(surf, pal["hair"], (int(head[0] - 0.5 * s), int(head[1] - 0.5 * s)), hr + 1, 0,
                           True, False, False, False)
        pygame.draw.circle(surf, pal["hair"], (int(head[0] - 1 * s), int(head[1] - 0.5 * s)), hr + 1, 0,
                           True, False, False, False)
        pygame.draw.rect(surf, pal["hair"], (int(head[0] - 6 * s), int(head[1] - 3 * s), Wd(4), Wd(7)))
    if "topknot" in ex:
        pygame.draw.circle(surf, pal["hair"], (int(head[0] - 1 * s), int(head[1] - 7 * s)), Wd(2.6))
        pygame.draw.line(surf, pal["hair"], (head[0] - 4 * s, head[1] - 3 * s), (head[0] - 1 * s, head[1] - 6 * s), Wd(2))
    if "ponytail" in ex:
        sway = math.sin(pose["chest"][0] * 0.5) * 2
        pygame.draw.line(surf, pal["hair"], (head[0] - 4 * s, head[1] - 2 * s), (head[0] - 9 * s, head[1] + (4 + sway) * s), Wd(3))
        pygame.draw.line(surf, shade(pal["hair"], 1.8), (head[0] - 5 * s, head[1] - 2 * s), (head[0] - 9 * s,
                                                                                         head[1] + (3 + sway) * s), 1)
    if "horns" in ex:
        hc = (226, 214, 186)
        for dx, lean in ((-3, -3), (2, 4)):
            pygame.draw.polygon(surf, hc, [(head[0] + dx * s - 1.8 * s, head[1] - 4 * s),
                                           (head[0] + dx * s + 1.8 * s, head[1] - 4 * s),
                                           (head[0] + (dx + lean) * s, head[1] - 10 * s)])
            pygame.draw.line(surf, shade(hc, 0.6), (head[0] + dx * s + 1.5 * s, head[1] - 4 * s),
                             (head[0] + (dx + lean) * s, head[1] - 10 * s), 1)
    if "beard" in ex:
        pygame.draw.polygon(surf, (236, 236, 240), [(head[0] + 1 * s, head[1] + 3 * s), (head[0] + 5 * s, head[1] + 2 * s),
                                                    (head[0] + 3 * s, head[1] + 11 * s), (head[0] - 2 * s, head[1] + 6 * s)])
        pygame.draw.line(surf, (190, 190, 200), (head[0] + 2 * s, head[1] + 4 * s), (head[0] + 2 * s, head[1] + 9 * s), 1)
    if "mask" in ex:
        mc = pal["mask"] or (50, 40, 72)
        pygame.draw.polygon(surf, mc, [(head[0] - 3 * s, head[1] + 1 * s), (head[0] + 6 * s, head[1] + 1 * s),
                                       (head[0] + 4 * s, head[1] + 6 * s), (head[0] - 2 * s, head[1] + 6 * s)])
    band = pal["band"]
    if "band" in ex and band:
        pygame.draw.line(surf, band, (head[0] - 5.5 * s, head[1] - 2.5 * s), (head[0] + 5.5 * s, head[1] - 2.5 * s), Wd(2))
        fl = math.sin(pose["chest"][0] * 0.4 + pose["head"][1]) * 1.5
        pygame.draw.line(surf, band, (head[0] - 5 * s, head[1] - 2.5 * s), (head[0] - 11 * s, head[1] + (-1 + fl) * s), Wd(1.6))
        pygame.draw.line(surf, shade(band, 0.75), (head[0] - 5 * s, head[1] - 1.5 * s), (head[0] - 10 * s,
                                                                                      head[1] + (2 + fl) * s), 1)
    if "brow" in ex:
        pygame.draw.line(surf, skin_d, (head[0] + 0 * s, head[1] - 1.5 * s), (head[0] + 5 * s, head[1] - 1.5 * s), Wd(2))
    # eye
    ey = (int(head[0] + 2.4 * s), int(head[1] - 0.4 * s))
    surf.fill((250, 250, 250), (ey[0] - (1 if s > 1.2 else 0), ey[1], Wd(2.4), Wd(1.6)))
    surf.fill((20, 12, 14), (ey[0] + Wd(1), ey[1], max(1, Wd(1.4)), Wd(1.6)))
    pygame.draw.line(surf, (30, 16, 18), (ey[0] - 1, ey[1] - max(1, int(s)) - 1), (ey[0] + Wd(3), ey[1] - max(1, int(s)) - 1), 1)
    if "hat" in ex:
        st = (214, 190, 120) if pal["robe"] is None else shade(pal["robe"], 1.1)
        pygame.draw.polygon(surf, st, [(head[0] - 9 * s, head[1] - 3 * s), (head[0] + 9 * s, head[1] - 3 * s),
                                       (head[0] + 1 * s, head[1] - 16 * s)])
        pygame.draw.line(surf, shade(st, 1.4), (head[0] - 8 * s, head[1] - 3 * s), (head[0] + 1 * s, head[1] - 15 * s), 1)
        pygame.draw.line(surf, shade(st, 0.6), (head[0] - 9 * s, head[1] - 3 * s), (head[0] + 9 * s, head[1] - 3 * s), Wd(1.6))
        pygame.draw.circle(surf, pal["belt"], (int(head[0] + 1 * s), int(head[1] - 9 * s)), max(1, Wd(1.2)))

    # front arm
    sleeve_f = skin if bare else gi
    _limb(surf, [sh_f, el_f], Wd(3.8), sleeve_f, shade(sleeve_f, 1.25))
    _limb(surf, [el_f, hand_f], Wd(3.2), skin, shade(skin, 1.15))
    if not bare:
        pygame.draw.circle(surf, pal["belt"], (int(el_f[0] * 0.3 + hand_f[0] * 0.7), int(el_f[1] * 0.3 + hand_f[1] * 0.7)),
                           max(1, Wd(1.8)))
    pygame.draw.circle(surf, skin, (int(hand_f[0]), int(hand_f[1])), Wd(2.6))
    pygame.draw.circle(surf, shade(skin, 1.2), (int(hand_f[0] - 1), int(hand_f[1] - 1)), max(1, Wd(1)))

    if "staff" in pose:
        a, b2 = P(pose["staff"][0]), P(pose["staff"][1])
        pygame.draw.line(surf, shade(pal["staff"], 0.6), a, b2, Wd(3.4))
        pygame.draw.line(surf, pal["staff"], a, b2, Wd(2.4))
        pygame.draw.line(surf, shade(pal["staff"], 1.4), (a[0], a[1] - 1), (b2[0], b2[1] - 1), 1)
        for e in (a, b2):
            pygame.draw.circle(surf, pal["metal"], (int(e[0]), int(e[1])), Wd(2.2))
    if "blades" in ex and "bdir" in pose:
        dx, dy = pose["bdir"]
        for hnd in (hand_f, hand_b):
            tip = (hnd[0] + dx * 13 * s, hnd[1] + dy * 13 * s)
            pygame.draw.line(surf, (110, 120, 140), hnd, tip, Wd(3))
            pygame.draw.line(surf, (236, 244, 255), (hnd[0], hnd[1] - 1), (tip[0], tip[1] - 1), max(1, Wd(1.4)))
    return outlined(surf), (AX + 1, AY + 1)


_frame_cache = {}
_flip_cache = {}


def frame(ckey, cdef, pose_name, ph=0.0, flip=False):
    """Cached figure frame -> (surface, anchor). `flip` mirrors for facing left."""
    n = PHASES.get(pose_name, 1)
    q = int(ph * n) % n if n > 1 else 0
    key = (ckey, pose_name, q, flip)
    r = _frame_cache.get(key)
    if r is None:
        base_key = (ckey, pose_name, q, False)
        base = _frame_cache.get(base_key)
        if base is None:
            base = draw_figure(make_pose(pose_name, q / n if n > 1 else 0.0), cdef["pal"], cdef["ex"], cdef["scale"])
            _frame_cache[base_key] = base
        if not flip:
            return base
        surf, (ax, ay) = base
        r = (pygame.transform.flip(surf, True, False), (surf.get_width() - ax, ay))
        _frame_cache[key] = r
    return r


def white(surf):
    key = id(surf)
    w = _flip_cache.get(key)
    if w is None:
        w = pygame.mask.from_surface(surf, 40).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        _flip_cache[key] = w
    return w


# ----------------------------------------------------------------------------
# Props and projectiles
# ----------------------------------------------------------------------------
_prop = {}


def knife_sprite():
    if "knife" not in _prop:
        s = pygame.Surface((14, 5), SRCALPHA)
        pygame.draw.polygon(s, (230, 238, 250), [(0, 2), (9, 0), (13, 2), (9, 4)])
        pygame.draw.line(s, (130, 140, 170), (2, 3), (11, 3), 1)
        pygame.draw.rect(s, (110, 60, 40), (8, 0, 2, 5))
        _prop["knife"] = outlined(s)
    return _prop["knife"]


def disc_sprites():
    if "disc" not in _prop:
        out = []
        for k in range(4):
            s = pygame.Surface((17, 17), SRCALPHA)
            c = (8, 8)
            pygame.draw.circle(s, (130, 140, 170), c, 7)
            pygame.draw.circle(s, (230, 240, 255), c, 7, 1)
            for j in range(4):
                a = j * math.pi / 2 + k * math.pi / 8
                pygame.draw.polygon(s, (240, 250, 255), [c, (c[0] + math.cos(a) * 8, c[1] + math.sin(a) * 8),
                                                        (c[0] + math.cos(a + 0.5) * 6, c[1] + math.sin(a + 0.5) * 6)])
            pygame.draw.circle(s, (90, 40, 110), c, 2)
            out.append(outlined(s))
        _prop["disc"] = out
    return _prop["disc"]


def fireball_sprite(k):
    key = ("fire", k % 3)
    if key not in _prop:
        s = pygame.Surface((22, 22), SRCALPHA)
        c = (11, 11)
        r0 = 8 + (k % 3 - 1)
        for r, col in ((r0 + 2, (160, 40, 20, 90)), (r0, (240, 90, 30, 200)), (r0 - 3, (255, 190, 70, 255)),
                       (r0 - 6, (255, 250, 200, 255))):
            pygame.draw.circle(s, col, c, max(1, r))
        _prop[key] = s
    return _prop[key]


def pot_sprite():
    if "pot" not in _prop:
        s = pygame.Surface((16, 18), SRCALPHA)
        pygame.draw.ellipse(s, (170, 90, 52), (1, 4, 14, 14))
        pygame.draw.rect(s, (150, 76, 44), (4, 1, 8, 5))
        pygame.draw.ellipse(s, (210, 130, 80), (3, 6, 5, 6))
        pygame.draw.line(s, (240, 200, 90), (2, 10), (14, 10), 1)
        pygame.draw.line(s, (240, 200, 90), (4, 14), (12, 14), 1)
        _prop["pot"] = outlined(s)
    return _prop["pot"]


def snake_sprites():
    if "snake" not in _prop:
        out = []
        for k in range(4):
            s = pygame.Surface((30, 12), SRCALPHA)
            pts = []
            for i in range(0, 25):
                pts.append((26 - i, 8 + math.sin((i + k * 3) * 0.6) * 2.2 - (min(i, 6) * 0.0)))
            for i, p in enumerate(pts):
                col = (70, 150, 70) if (i // 3) % 2 == 0 else (46, 110, 56)
                pygame.draw.circle(s, col, (int(p[0]), int(p[1])), 2)
            pygame.draw.circle(s, (90, 180, 90), (27, 7), 3)
            s.set_at((28, 6), (255, 220, 60))
            s.set_at((29, 8), (230, 60, 60))
            out.append(outlined(s))
        _prop["snake"] = out
    return _prop["snake"]


_glow_cache = {}


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


def impact_star(size):
    key = ("star", size)
    s = _glow_cache.get(key)
    if s is None:
        s = pygame.Surface((size * 2 + 1,) * 2, SRCALPHA)
        c = size
        pygame.draw.polygon(s, (255, 255, 220), [(c, 0), (c + 2, c - 2), (2 * c, c), (c + 2, c + 2), (c, 2 * c),
                                                 (c - 2, c + 2), (0, c), (c - 2, c - 2)])
        pygame.draw.circle(s, (255, 255, 255), (c, c), max(2, size // 3))
        _glow_cache[key] = s
    return s


# ----------------------------------------------------------------------------
# Backgrounds
# ----------------------------------------------------------------------------
class Background:
    """Parallax temple interior: sky windows (far), painted wall + columns (mid), tiled floor."""

    FAR_P = 192
    COL_P = 128

    def __init__(self, key, seed=1):
        self.t = BGS[key]
        self.key = key
        rnd = random.Random(seed)
        t = self.t
        # far layer: wall mural + arched windows, period FAR_P
        far = pygame.Surface((self.FAR_P, GROUND - HUD_H + 4)).convert()
        dither_fill(far, (0, 0, self.FAR_P, far.get_height()), shade(t["wall"][0], 0.72), shade(t["wall"][1], 0.72), 8)
        self._mural(far, rnd)
        self.far = far
        # mid layer: wall detail band + columns + lanterns, period COL_P (transparent)
        mid = pygame.Surface((self.COL_P, GROUND - HUD_H + 4), SRCALPHA)
        self._columns(mid, rnd)
        self.mid = mid
        self.floor = self._floor()
        self.lanterns = [(self.COL_P // 2, 62)]
        self.motes = [[rnd.uniform(0, W), rnd.uniform(HUD_H, H), rnd.uniform(4, 16), rnd.uniform(0, 6)]
                      for _ in range(26)]
        self.t_anim = 0.0

    def _mural(self, s, rnd):
        t, P, h = self.t, self.FAR_P, s.get_height()
        c, hi, lo = t["far"], shade(t["far"], 1.25), shade(t["far"], 0.75)
        # brick courses
        for y in range(6, h, 12):
            pygame.draw.line(s, lo, (0, y), (P, y), 1)
            off = 0 if (y // 12) % 2 else 16
            for x in range(off, P, 32):
                pygame.draw.line(s, lo, (x, y), (x, y + 12), 1)
        # arched window showing the sky
        wx, wy, ww, wh = 70, 20, 52, 84
        sky = pygame.Surface((ww, wh))
        dither_fill(sky, (0, 0, ww, wh), t["sky"][0], t["sky"][1], 10)
        if self.key in ("moon", "spirit"):
            pygame.draw.circle(sky, t["mood"], (ww // 2 + 6, 26), 11)
            pygame.draw.circle(sky, t["sky"][0], (ww // 2 + 11, 23), 10)
            for _ in range(14):
                sky.set_at((rnd.randrange(ww), rnd.randrange(wh // 2)), (240, 240, 255))
        elif self.key == "inferno":
            for k in range(5):
                pygame.draw.polygon(sky, shade(t["sky"][1], 0.6 + k * 0.1),
                                    [(k * 12 - 4, wh), (k * 12 + 6, wh - 30 - (k * 7) % 22), (k * 12 + 16, wh)])
        else:
            pts = [(0, wh)]
            for x in range(0, ww + 6, 6):
                pts.append((x, wh - 20 - rnd.randint(0, 22)))
            pts.append((ww, wh))
            pygame.draw.polygon(sky, shade(t["far"], 0.9), pts)
        mask = pygame.Surface((ww, wh), SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, ww // 2, ww, wh - ww // 2))
        pygame.draw.circle(mask, (255, 255, 255, 255), (ww // 2, ww // 2), ww // 2)
        sky = sky.convert_alpha()
        sky.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        s.blit(sky, (wx, wy))
        pygame.draw.circle(s, t["gold"], (wx + ww // 2, wy + ww // 2), ww // 2 + 2, 2)
        pygame.draw.lines(s, t["gold"], False, [(wx - 2, wy + ww // 2), (wx - 2, wy + wh), (wx + ww + 2, wy + wh),
                                                (wx + ww + 2, wy + ww // 2)], 2)
        for k in range(1, 3):
            pygame.draw.line(s, shade(t["gold"], 0.7), (wx + k * ww // 3, wy + 4), (wx + k * ww // 3, wy + wh), 1)
        # painted dragon scroll banner either side
        for bx in (14, 150):
            pygame.draw.rect(s, shade(t["pillar"], 0.8), (bx, 10, 28, 70))
            pygame.draw.rect(s, t["gold"], (bx, 10, 28, 70), 1)
            pygame.draw.rect(s, t["gold"], (bx - 2, 8, 32, 3))
            pygame.draw.rect(s, t["gold"], (bx - 2, 79, 32, 3))
            pts = [(bx + 6 + math.sin(i * 0.55) * 7, 20 + i * 2.6) for i in range(20)]
            pygame.draw.lines(s, t["gold"], False, pts, 2)
            pygame.draw.circle(s, t["gold"], (int(pts[-1][0]), int(pts[-1][1])), 3)
            pygame.draw.circle(s, shade(t["pillar"], 0.8), (int(pts[0][0]) + 1, int(pts[0][1]) + 1), 1)
        # base wainscot
        pygame.draw.rect(s, shade(t["pillar"], 0.55), (0, h - 22, P, 22))
        pygame.draw.line(s, t["gold"], (0, h - 22), (P, h - 22), 1)
        for x in range(0, P, 24):
            pygame.draw.rect(s, shade(t["pillar"], 0.7), (x + 3, h - 18, 18, 14), 1)

    def _columns(self, s, rnd):
        t, P, h = self.t, self.COL_P, s.get_height()
        cx, cw = 4, 22
        for x0 in (cx, cx + P - 0):          # tile seams
            pass
        col = t["pillar"]
        body = pygame.Rect(cx, 0, cw, h)
        pygame.draw.rect(s, col, body)
        pygame.draw.rect(s, shade(col, 1.35), (cx + 2, 0, 4, h))
        pygame.draw.rect(s, shade(col, 0.6), (cx + cw - 6, 0, 6, h))
        for y in range(8, h, 20):
            pygame.draw.line(s, shade(col, 0.5), (cx, y), (cx + cw - 1, y), 1)
        pygame.draw.rect(s, t["gold"], (cx - 3, 0, cw + 6, 6))
        pygame.draw.rect(s, shade(t["gold"], 0.7), (cx - 3, 4, cw + 6, 2))
        pygame.draw.rect(s, t["gold"], (cx - 3, h - 28, cw + 6, 6))
        pygame.draw.rect(s, shade(t["gold"], 0.7), (cx - 3, h - 24, cw + 6, 2))
        pygame.draw.rect(s, shade(col, 0.45), (cx - 2, h - 18, cw + 4, 18))
        pygame.draw.rect(s, t["gold"], (cx - 2, h - 18, cw + 4, 18), 1)
        # hanging lantern between columns
        lx, ly = P // 2 + 14, 30
        pygame.draw.line(s, shade(t["gold"], 0.6), (lx, 6), (lx, ly - 8), 1)
        pygame.draw.ellipse(s, shade(t["glow"], 0.55), (lx - 7, ly - 8, 14, 18))
        pygame.draw.ellipse(s, t["glow"], (lx - 5, ly - 6, 10, 14))
        pygame.draw.ellipse(s, shade(t["glow"], 1.4), (lx - 2, ly - 3, 4, 7))
        for yy in (ly - 7, ly + 9):
            pygame.draw.rect(s, t["gold"], (lx - 4, yy, 8, 2))
        pygame.draw.line(s, t["glow"], (lx, ly + 11), (lx, ly + 18), 1)
        self.lantern_pos = (lx, ly + 2)

    def _floor(self):
        t = self.t
        h = H - GROUND + 6
        s = pygame.Surface((256, h)).convert()
        dither_fill(s, (0, 0, 256, h), t["floor"][0], t["floor"][1], 6)
        for y, hh in ((0, 4), (10, 7), (24, 9)):
            pass
        for k, y in enumerate((0, 9, 21)):
            for x in range(-(k * 13) % 48 - 48, 256, 48):
                pygame.draw.rect(s, shade(t["floor"][0], 0.72), (x, y, 48, 1))
                pygame.draw.rect(s, shade(t["floor"][0], 0.72), (x, y, 1, 9 + k * 3))
                pygame.draw.rect(s, shade(t["floor"][0], 1.18), (x + 1, y + 1, 46, 1))
        pygame.draw.rect(s, shade(t["floor"][0], 1.35), (0, 0, 256, 2))
        pygame.draw.rect(s, shade(t["floor"][0], 0.5), (0, 2, 256, 1))
        return s

    def update(self, dt):
        self.t_anim += dt
        for m in self.motes:
            m[1] -= m[2] * dt * (0.6 if self.key != "inferno" else 1.4)
            m[0] += math.sin(self.t_anim + m[3]) * 8 * dt
            if m[1] < HUD_H:
                m[1] = H
                m[0] = random.uniform(0, W)

    def draw(self, surf, cam):
        top = HUD_H - 4
        # ceiling beam (visible on menu screens where there is no HUD)
        surf.fill(shade(self.t["wall"][0], 0.35), (0, 0, W, top))
        for x in range(-int(cam * 0.9) % 48 - 48, W, 48):
            surf.fill(shade(self.t["pillar"], 0.45), (x, 0, 4, top))
        surf.fill(self.t["gold"], (0, top - 3, W, 1))
        surf.fill(shade(self.t["gold"], 0.6), (0, top - 2, W, 2))
        # far wall (slow parallax)
        fo = int(cam * 0.45) % self.FAR_P
        for x in range(-fo, W, self.FAR_P):
            surf.blit(self.far, (x, top))
        # mid columns
        mo = int(cam) % self.COL_P
        for x in range(-mo, W + self.COL_P, self.COL_P):
            surf.blit(self.mid, (x, top))
        # lantern glow
        lx, ly = self.lantern_pos
        flick = 1.0 + math.sin(self.t_anim * 7.0) * 0.06 + math.sin(self.t_anim * 3.1) * 0.05
        g = glow(int(30 * flick), self.t["glow"])
        for x in range(-mo, W + self.COL_P, self.COL_P):
            surf.blit(g, (x + lx - g.get_width() // 2, top + ly - g.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)
        # floor
        fo2 = int(cam) % 256
        for x in range(-fo2, W, 256):
            surf.blit(self.floor, (x, GROUND - 2))
        # floor reflection of lantern light
        ref = pygame.Surface((W, 8), SRCALPHA)
        ref.fill((0, 0, 0, 0))
        for x in range(-mo, W + self.COL_P, self.COL_P):
            pygame.draw.ellipse(ref, (*self.t["glow"], 36), (x + lx - 20, 0, 40, 6))
        surf.blit(ref, (0, GROUND - 1))

    def draw_motes(self, surf):
        c = self.t["motes"]
        for x, y, _, ph in self.motes:
            a = 0.5 + 0.5 * math.sin(self.t_anim * 2 + ph)
            col = shade(c, 0.5 + 0.5 * a)
            surf.fill(col, (int(x), int(y), 1 if a < 0.7 else 2, 1 if a < 0.7 else 2))


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
LACQ = (96, 24, 28)
GOLD = (238, 190, 84)


def panel(surf, rect, base=LACQ, trim=GOLD):
    rect = pygame.Rect(rect)
    surf.fill(base, rect)
    surf.fill(shade(base, 1.25), (rect.x + 1, rect.y + 1, rect.w - 2, 1))
    surf.fill(shade(base, 0.7), (rect.x + 1, rect.bottom - 2, rect.w - 2, 1))
    pygame.draw.rect(surf, trim, rect, 1)
    for p in ((rect.x + 1, rect.y + 1), (rect.right - 3, rect.y + 1), (rect.x + 1, rect.bottom - 3),
              (rect.right - 3, rect.bottom - 3)):
        surf.fill(trim, (*p, 2, 2))


def hud_bar():
    s = pygame.Surface((W, HUD_H)).convert()
    s.fill((26, 12, 16))
    dither_fill(s, (0, 0, W, HUD_H), (74, 20, 26), (36, 12, 18), 4)
    pygame.draw.line(s, GOLD, (0, HUD_H - 1), (W, HUD_H - 1), 1)
    pygame.draw.line(s, shade(GOLD, 0.55), (0, HUD_H - 2), (W, HUD_H - 2), 1)
    return s


def energy_bar(surf, x, y, w, h, frac, col, label=None, segs=24):
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surf, (12, 6, 8), (x - 1, y - 1, w + 2, h + 2))
    surf.fill((52, 22, 24), (x, y, w, h))
    cw = int(w * frac)
    if cw > 0:
        surf.fill(col, (x, y, cw, h))
        surf.fill(shade(col, 1.45), (x, y, cw, 1))
        surf.fill(shade(col, 0.65), (x, y + h - 1, cw, 1))
    for k in range(1, segs):
        sx = x + w * k // segs
        surf.fill((18, 8, 10), (sx, y, 1, h))
    pygame.draw.rect(surf, GOLD, (x - 1, y - 1, w + 2, h + 2), 1)


def draw_head_icon(surf, x, y):
    c = (58, 168, 164)
    pygame.draw.circle(surf, (238, 186, 140), (x, y), 4)
    pygame.draw.circle(surf, (30, 22, 26), (x, y - 1), 4, 0, True, True, False, False)
    pygame.draw.line(surf, (220, 40, 50), (x - 4, y - 1), (x + 4, y - 1), 1)
    pygame.draw.line(surf, (220, 40, 50), (x - 4, y - 1), (x - 7, y + 1), 1)
    surf.set_at((x + 2, y), (20, 12, 14))
    pygame.draw.line(surf, c, (x - 3, y + 4), (x + 3, y + 4), 2)
