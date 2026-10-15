"""The five temple guardians. Each boss runs a generator-based move script (windup -> strike -> recovery)
so every attack is telegraphed, but they block, read your stance, get armour while winding up, and speed up
as their health drops (three phases), which is what makes them much tougher than the common enemies.
"""
import math
import random

import pygame

import gfx
from config import W, GROUND, CHARS, BOSSES
from fighters import Proj, wrect, sign, clamp

GRAV = 900.0


class Boss:
    def __init__(self, idx, g):
        self.cfg = BOSSES[idx]
        self.idx = idx
        self.key = self.cfg["key"]
        self.char = CHARS[self.key]
        self.s = self.char["scale"]
        t = g.tune
        self.max_hp = int(self.cfg["hp"] * t["hp"])
        self.hp = self.max_hp
        self.dmgk = t["dmg"]
        self.spd = t["spd"]
        self.base_speed = self.cfg["speed"] * self.spd
        self.x = float(g.cam + W + 50)
        self.z = self.vz = self.vx = 0.0
        self.facing = -1
        self.state = "intro"
        self.gen = None
        self.wait = 0.0
        self.atk = None
        self.armor = False
        self.invuln = 0.0
        self.flash = 0.0
        self.alpha = 255
        self.neutral = 0.8
        self.block_t = 0.0
        self.block_cd = 0.0
        self.stun = 0.0
        self.hurt_t = 0.0
        self.combo = 0
        self.combo_t = 0.0
        self.phase = 0
        self.dead_t = 0.0
        self.alive = True
        self.pose_name = "idle"
        self.ph = 0.0
        self.anim = 0.0
        self.t = 0.0
        self.counter = False
        self.roar_t = 0.0
        self.aura = 0

    # ---- scaling helpers
    @property
    def tk(self):
        return (1.0, 0.84, 0.7)[self.phase]

    @property
    def speed(self):
        return self.base_speed * (1.0, 1.12, 1.25)[self.phase]

    def idle_pose(self):
        return "staff_idle" if self.key == "hu" else "idle"

    def walk_pose(self):
        return "staff_walk" if self.key == "hu" else "walk"

    def hurtbox(self):
        s = self.s
        return wrect(self.x, 1, (-7 * s, 7 * s, -46 * s, 0), self.z)

    def attack_rect(self):
        if not self.atk:
            return None
        return wrect(self.x, self.facing, self.atk["rect"], self.z)

    def face(self, g):
        self.facing = 1 if g.player.x > self.x else -1

    def strike(self, rect, dmg, tick=0.0, kb=1.0):
        self.atk = dict(rect=rect, dmg=dmg * self.dmgk, tick=tick, kb=kb, hit=False)

    def stop(self):
        self.atk = None

    # ---- damage taken
    def hit(self, dmg, g, p):
        if self.state != "fight" or self.invuln > 0 or self.alpha < 250:
            return False
        if self.block_t > 0:
            g.audio.play("block")
            g.spark(self.x + self.facing * 10 * self.s, GROUND - 28 * self.s)
            self.invuln = 0.12
            self.counter = True
            return "blocked"
        mult = 1.5 if self.stun > 0 else 1.0
        self.hp -= max(1, round(dmg * mult))
        self.flash = 0.12
        self.invuln = 0.2
        self.combo += 1
        self.combo_t = 1.3
        if self.hp <= 0:
            self.die(g, p)
            return "killed"
        self._check_phase(g)
        if not self.armor and self.stun <= 0:
            self.gen = None
            self.atk = None
            self.vx = sign(self.x - p.x) * 70 * (1.0 if self.s < 1.3 else 0.5)
            self.hurt_t = 0.28
            self.neutral = 0.3 + 0.1 * self.phase
            if self.combo >= 3:                       # you can't just chain him forever
                self.combo = 0
                self.counter = True
        return "hit"

    def _check_phase(self, g):
        frac = self.hp / self.max_hp
        ph = 0 if frac > 0.66 else 1 if frac > 0.33 else 2
        if ph > self.phase:
            self.phase = ph
            self.gen = self._roar(g)
            self.wait = 0.0
            self.atk = None
            self.hurt_t = 0.0
            self.stun = 0.0
            self.armor = True

    def _roar(self, g):
        self.invuln = 1.0
        self.pose_name = "burst_w"
        self.aura = 1
        g.audio.play("roar")
        g.flash_screen(0.3)
        g.shake = max(g.shake, 5)
        g.ring(self.x, GROUND - 24 * self.s, (255, 200, 120))
        g.projs = [p for p in g.projs if p.owner is not self]
        yield 0.9
        self.aura = 0
        self.armor = False
        self.neutral = 0.3

    def die(self, g, p):
        self.state = "dead"
        self.dead_t = 0.0
        self.atk = None
        self.gen = None
        self.vx = sign(self.x - p.x) * 50
        self.vz = 150
        g.on_boss_dead(self)

    # ---- update
    def update(self, dt, g):
        p = g.player
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.block_cd = max(0.0, self.block_cd - dt)
        if self.combo_t > 0:
            self.combo_t -= dt
            if self.combo_t <= 0:
                self.combo = 0
        if self.state == "dead":
            self.dead_t += dt
            self.x += self.vx * dt
            self.vx *= 0.96
            self.z += self.vz * dt
            self.vz -= GRAV * dt
            if self.z <= 0:
                self.z, self.vz = 0.0, 0.0
            return
        if self.state == "intro":
            self.facing = -1
            self.x -= 70 * dt
            self.anim += dt * 1.6
            self.pose_name = self.walk_pose()
            self.ph = self.anim % 1
            if self.x <= g.cam + W - 90:
                self.state = "fight"
                self.neutral = 0.7
            return
        # physics
        if self.z > 0 or self.vz > 0:
            self.z += self.vz * dt
            self.vz -= GRAV * dt
            if self.z <= 0:
                self.z, self.vz = 0.0, 0.0
                g.audio.play("land", 0.7)
                g.dust(self.x, GROUND, 4)
        self.x += self.vx * dt
        self.x = clamp(self.x, g.cam + 14, g.cam + W - 14)
        if self.alpha < 255 and self.gen is None:
            self.alpha = min(255, self.alpha + 600 * dt)

        if self.hurt_t > 0:
            self.hurt_t -= dt
            self.vx *= 0.9
            self.pose_name = "hurt"
            return
        if self.stun > 0:
            self.stun -= dt
            self.vx = 0
            self.pose_name = "stun"
            if self.stun <= 0:
                self.neutral = 0.3
            return
        if self.block_t > 0:
            self.block_t -= dt
            self.pose_name = "block"
            if self.block_t <= 0:
                self.block_cd = 1.4
            return

        if self.gen is not None:
            self.wait -= dt
            guard = 0
            while self.wait <= 0 and self.gen is not None and guard < 8:
                guard += 1
                try:
                    self.wait = next(self.gen)
                except StopIteration:
                    self.gen = None
                    self.atk = None
                    self.armor = False
                    self.vx = 0
                    self.neutral = random.uniform(0.15, 0.55) * self.tk
                    self.aura = 0
            return

        # ---- neutral: space out, maybe block, choose a move
        self.face(g)
        d = abs(p.x - self.x)
        self.vx = 0
        a = p.attack_rect()
        if (a and self.block_cd <= 0 and self.cfg["block"] > 0 and d < 52 and not self.counter
                and random.random() < self.cfg["block"] * 0.1):
            self.block_t = 0.45
            g.audio.play("tick", 0.5)
            return
        if self.counter:
            self.counter = False
            self._start(self._counter_move(d), g)
            return
        self.pose_name = self.idle_pose()
        want = 62 if self.s < 1.3 else 52
        if d > want + 10:
            self.x += self.facing * self.speed * dt
            self.anim += dt * 1.6
            self.pose_name = self.walk_pose()
            self.ph = self.anim % 1
        elif d < want - 28 and random.random() < 0.02:
            self.x -= self.facing * self.speed * dt * 8
        self.neutral -= dt
        if self.neutral <= 0:
            self._start(self._choose(d, g), g)

    def _counter_move(self, d):
        return {"hu": "thrust", "mei": "slash", "gorr": "swing", "sen": "burst", "zhao": "combo"}[self.key]

    def _choose(self, d, g):
        moves = [(n, w) for n, w, lo, hi in self.cfg["moves"] if lo <= d <= hi]
        if not moves:
            moves = [(n, w) for n, w, lo, hi in self.cfg["moves"]]
        # recently used moves are less likely: stops spamming one attack
        pool = []
        for n, w in moves:
            if n == getattr(self, "last", None):
                w = max(1, w // 3)
            pool += [n] * w
        return random.choice(pool)

    def _start(self, name, g):
        self.last = name
        self.gen = MOVES[name](self, g)
        self.wait = 0.0
        self.atk = None

    # ---- draw
    def draw(self, surf, cam):
        sx = int(self.x - cam)
        sy = int(GROUND - self.z)
        name = self.pose_name
        if self.state == "dead":
            name = "hurt" if self.dead_t < 0.45 else "dead"
        ph = self.ph
        img, (ax, ay) = gfx.frame(self.key, self.char, name, ph % 1.0, self.facing < 0)
        sw = int(26 * self.s)
        sh = pygame.Surface((sw * 2, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), (0, 0, sw * 2, 7))
        surf.blit(sh, (sx - sw, GROUND - 3))
        if self.alpha < 255:
            img = img.copy()
            img.set_alpha(int(self.alpha))
        pos = (sx - ax, sy - ay)
        if self.state == "dead" and self.dead_t > 1.2:
            img = img.copy()
            img.set_alpha(max(0, 255 - int((self.dead_t - 1.2) * 300)))
        surf.blit(img, pos)
        if self.flash > 0 and self.alpha > 200:
            surf.blit(gfx.white(img), pos)
        if self.stun > 0:
            for k in range(3):
                a = self.t * 7 + k * 2.1
                gx, gy = sx + math.cos(a) * 12, sy - 52 * self.s + math.sin(a) * 4
                pygame.draw.circle(surf, (255, 235, 90), (int(gx), int(gy)), 2)
        if self.aura:
            surf.blit(gfx.glow(int(30 * self.s), (160, 70, 30)), (sx - int(30 * self.s), sy - int(60 * self.s)),
                      special_flags=pygame.BLEND_RGB_ADD)
        if self.atk and self.atk["rect"][1] - self.atk["rect"][0] > 70 and False:
            pass


# =============================================================================
# Move scripts. Each is a generator yielding the number of seconds to wait.
# =============================================================================
def _stance_low(g):
    p = g.player
    return p.crouch and p.on_ground


def mv_thrust(b, g, quick=False):
    b.face(g)
    low = _stance_low(g) or random.random() < 0.3
    b.armor = True
    b.pose_name = "staff_lo_w" if low else "staff_hi_w"
    yield 0.44 * b.tk
    b.face(g) if False else None
    g.audio.play("whoosh")
    b.pose_name = "staff_lo" if low else "staff_hi"
    r = 68
    b.strike((6, r, -12, -1) if low else (6, r, -49, -31), 8)
    b.vx = b.facing * 55
    yield 0.17
    b.stop()
    b.vx = 0
    b.armor = False
    b.pose_name = "staff_idle"
    yield 0.4 * b.tk


def mv_spin(b, g):
    b.face(g)
    b.armor = True
    b.pose_name = "staff_lo_w"
    yield 0.5 * b.tk
    b.pose_name = "spin"
    b.strike((-50, 50, -27, 0), 8, tick=0.4)
    b.vx = b.facing * 62 * b.spd
    g.audio.play("whoosh")
    for i in range(16):
        b.ph = (i * 0.125) % 1
        if i % 5 == 0:
            g.audio.play("whoosh", 0.5)
        yield 0.055
    b.stop()
    b.vx = 0
    b.armor = False
    b.stun = 0.75                      # dizzy: your opening
    b.pose_name = "stun"
    yield 0.0


def _land(b):
    while b.z > 0 or b.vz > 0:
        yield 0.02


def mv_leap(b, g):
    b.face(g)
    b.armor = True
    b.pose_name = "dash_w"
    yield 0.32 * b.tk
    air = 2 * 300 / GRAV
    tx = clamp(g.player.x - b.facing * 38, g.cam + 20, g.cam + W - 20)
    b.vz = 300
    b.vx = (tx - b.x) / air
    b.pose_name = "jump"
    g.audio.play("jump", 0.6)
    yield 0.3
    b.strike((-14, 16, -34, 0), 9)
    yield from _land(b)
    b.stop()
    b.vx = 0
    b.face(g)
    b.pose_name = "staff_hi_w"
    yield 0.28 * b.tk
    g.audio.play("whoosh")
    b.pose_name = "staff_hi"
    b.strike((6, 66, -49, -31), 8)
    yield 0.16
    b.stop()
    b.armor = False
    b.pose_name = "staff_idle"
    yield 0.45 * b.tk


def mv_discs(b, g):
    b.face(g)
    n = 2 + (1 if b.phase >= 1 else 0) + (1 if b.phase >= 2 else 0)
    hi = not _stance_low(g)
    for i in range(n):
        b.face(g)
        b.pose_name = "blade_w"
        yield 0.32 * b.tk
        b.pose_name = "throw"
        y = GROUND - (38 if hi else 9)
        g.projs.append(Proj("disc", b.x + b.facing * 14, y, b.facing * 205 * b.spd, 6 * b.dmgk, b,
                            range=170 + 20 * b.phase, life=3.2))
        g.audio.play("knife")
        yield 0.3 * b.tk
        hi = not hi
    b.pose_name = "idle"
    yield 0.35 * b.tk


def mv_dash(b, g, quick=False):
    b.face(g)
    k = 0.6 if quick else 1.0
    b.armor = True
    b.pose_name = "dash_w"
    yield 0.32 * b.tk * k
    legs = 1 + (1 if b.phase >= 1 and not quick else 0)
    for i in range(legs):
        b.pose_name = "dash"
        g.audio.play("whoosh")
        b.vx = b.facing * 340 * b.spd
        b.strike((6, 34, -41, -8), 7)
        yield 0.3
        b.stop()
        b.vx = 0
        if i + 1 < legs:
            b.facing = -b.facing
            b.pose_name = "dash_w"
            yield 0.2 * b.tk
    b.armor = False
    b.pose_name = "idle"
    yield 0.5 * b.tk * k


def mv_jumpslash(b, g):
    b.face(g)
    b.armor = True
    b.pose_name = "blade_up"
    yield 0.25 * b.tk
    b.vz = 300
    b.vx = b.facing * 40
    b.pose_name = "jump"
    g.audio.play("jump", 0.6)
    yield 0.34
    b.face(g)
    b.pose_name = "dive"
    b.vz = -320
    b.vx = (g.player.x - b.x) / 0.28
    b.strike((-10, 24, -32, 0), 9)
    g.audio.play("whoosh")
    yield from _land(b)
    b.stop()
    b.vx = 0
    b.armor = False
    b.pose_name = "idle"
    yield 0.55 * b.tk


def mv_slash(b, g):
    for i in range(2):
        b.face(g)
        b.armor = True
        b.pose_name = "blade_w"
        yield 0.25 * b.tk
        b.pose_name = "blade"
        g.audio.play("whoosh")
        b.strike((4, 40, -42, -10), 6)
        b.vx = b.facing * 70
        yield 0.14
        b.stop()
        b.vx = 0
        yield 0.1
    b.armor = False
    b.pose_name = "idle"
    yield 0.42 * b.tk


def mv_stomp(b, g):
    b.face(g)
    b.armor = True
    b.pose_name = "stomp_w"
    yield 0.72 * b.tk
    for i in range(1 + b.phase):
        b.pose_name = "slam"
        g.audio.play("boom")
        g.shake = max(g.shake, 6)
        g.dust(b.x + b.facing * 18, GROUND, 8)
        for d in (-1, 1):
            g.projs.append(Proj("wave", b.x + d * 20, GROUND - 8, d * (150 + 25 * b.phase) * b.spd, 8 * b.dmgk, b,
                                life=2.4))
        yield 0.4 * b.tk
        if i + 1 < 1 + b.phase:
            b.pose_name = "stomp_w"
            yield 0.3 * b.tk
    b.armor = False
    b.pose_name = "slam"
    yield 0.6 * b.tk


def mv_charge(b, g):
    b.face(g)
    b.armor = True
    b.pose_name = "dash_w"
    g.audio.play("roar", 0.6)
    yield 0.75 * b.tk
    b.pose_name = "run"
    g.audio.play("whoosh")
    b.vx = b.facing * 250 * b.spd
    b.strike((0, 44, -24, 0), 10)
    t = 0.0
    while t < 1.5:
        b.ph = (b.ph + 0.12) % 1
        if (b.facing > 0 and b.x >= g.cam + W - 18) or (b.facing < 0 and b.x <= g.cam + 18):
            break
        t += 0.03
        if int(t * 100) % 12 == 0:
            g.dust(b.x - b.facing * 10, GROUND, 2)
        yield 0.03
    b.stop()
    b.vx = 0
    g.audio.play("boom")
    g.shake = max(g.shake, 8)
    b.armor = False
    b.stun = 1.25 if b.phase < 2 else 0.9
    b.pose_name = "stun"
    yield 0.0


def mv_swing(b, g, quick=False):
    k = 0.65 if quick else 1.0
    b.face(g)
    b.armor = True
    b.pose_name = "slam_w"
    yield 0.55 * b.tk * k
    b.pose_name = "slam"
    g.audio.play("whoosh")
    b.strike((6, 52, -50, -31), 10, kb=1.3)
    yield 0.18
    b.stop()
    b.armor = False
    yield 0.55 * b.tk * k


def mv_fireballs(b, g):
    b.face(g)
    n = 3 + b.phase
    hi = random.random() < 0.5
    for i in range(n):
        b.face(g)
        b.pose_name = "cast_hi" if hi else "cast_lo"
        yield 0.34 * b.tk
        g.projs.append(Proj("fire", b.x + b.facing * 16, GROUND - (38 if hi else 9), b.facing * (150 + 18 * b.phase) * b.spd,
                            6 * b.dmgk, b, life=4.0))
        g.audio.play("fire", 0.6)
        yield 0.2 * b.tk
        hi = not hi
    b.pose_name = "idle"
    yield 0.42 * b.tk


def mv_teleport(b, g):
    b.armor = True
    b.pose_name = "cast"
    g.audio.play("tick")
    for i in range(6):
        b.alpha = max(0, 255 - (i + 1) * 45)
        yield 0.04
    b.invuln = 0.4
    p = g.player
    side = -p.facing
    nx = p.x + side * 78
    if not (g.cam + 24 < nx < g.cam + W - 24):
        nx = p.x - side * 78
    b.x = clamp(nx, g.cam + 20, g.cam + W - 20)
    g.spark(b.x, GROUND - 30)
    g.audio.play("spark")
    yield 0.3 * b.tk
    b.face(g)
    for i in range(6):
        b.alpha = min(255, (i + 1) * 45)
        yield 0.03
    b.alpha = 255
    yield 0.18 * b.tk
    r = random.random()
    b.armor = False
    if r < 0.45 or b.phase == 0:
        yield from mv_burst(b, g)
    else:
        yield from mv_fireballs(b, g)


def mv_summon(b, g):
    b.face(g)
    b.armor = True
    b.pose_name = "cast"
    b.aura = 1
    g.audio.play("roar", 0.5)
    yield 0.8 * b.tk
    if g.minion_count() < 3:
        for sx in (g.cam - 10, g.cam + W + 10):
            g.spawn_enemy("imp", sx)
    b.aura = 0
    b.armor = False
    yield 0.55 * b.tk


def mv_burst(b, g):
    b.face(g)
    b.armor = True
    b.pose_name = "burst_w"
    b.aura = 1
    g.audio.play("tick")
    yield 0.72 * b.tk
    b.pose_name = "burst"
    b.aura = 2
    g.audio.play("boom")
    g.shake = max(g.shake, 6)
    g.ring(b.x, GROUND - 24 * b.s, (255, 150, 70), big=True)
    b.strike((-40, 40, -52, 0), 9, kb=1.3)
    yield 0.24
    b.stop()
    b.aura = 0
    b.armor = False
    yield 0.6 * b.tk


def mv_flame(b, g):
    b.face(g)
    b.armor = True
    b.pose_name = "flame_w"
    yield 0.65 * b.tk
    b.pose_name = "flame"
    g.audio.play("fire")
    b.strike((10, 108, -34, -3), 5, tick=0.32)
    t = 0.0
    while t < 1.0:
        g.flame_breath(b.x + b.facing * 12 * b.s, GROUND - 32 * b.s, b.facing)
        t += 0.05
        yield 0.05
    b.stop()
    b.armor = False
    yield 0.65 * b.tk


def mv_combo(b, g):
    yield from mv_dash(b, g, quick=True)
    b.face(g)
    yield from mv_swing(b, g, quick=True)
    if b.phase >= 1:
        b.face(g)
        yield from mv_stomp(b, g)


MOVES = dict(thrust=mv_thrust, spin=mv_spin, leap=mv_leap, discs=mv_discs, dash=mv_dash, jumpslash=mv_jumpslash,
             slash=mv_slash, stomp=mv_stomp, charge=mv_charge, swing=mv_swing, fireballs=mv_fireballs,
             teleport=mv_teleport, summon=mv_summon, burst=mv_burst, flame=mv_flame, combo=mv_combo)
