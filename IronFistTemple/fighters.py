"""Player, regular enemies, projectiles and floor hazards."""
import math
import random

import pygame

import gfx
from config import (W, H, GROUND, PLAYER_HP, PLAYER_SPEED, JUMP_V, GRAVITY, ATTACKS, CHARS)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def wrect(x, facing, rel, z=0.0):
    """World rect for a box given relative to the feet: rel = (x0, x1, y0, y1), y negative = up."""
    x0, x1, y0, y1 = rel
    a, b = x + facing * x0, x + facing * x1
    return pygame.Rect(int(round(min(a, b))), int(round(GROUND - z + y0)), max(1, int(round(abs(b - a)))),
                       max(1, int(y1 - y0)))


def sign(v):
    return 1 if v >= 0 else -1


# =============================================================================
# Player
# =============================================================================
class Input:
    mx = 0
    down = False
    jump = punch = kick = False
    dir = 0


class Player:
    def __init__(self):
        self.char = CHARS["hero"]
        self.reset(40)

    def reset(self, x):
        self.x, self.z, self.vz, self.vx = float(x), 0.0, 0.0, 0.0
        self.facing = 1
        self.hp = PLAYER_HP
        self.atk = None
        self.atk_t = 0.0
        self.hit_ids = set()
        self.air_atk = False
        self.crouch = False
        self.invuln = 0.0
        self.hurt_t = 0.0
        self.kvx = 0.0
        self.grips = []
        self.shake = 0
        self.last_dir = 0
        self.anim = 0.0
        self.dead_t = 0.0
        self.dead = False
        self.victory = False
        self.step_t = 0.0
        self.used = set()
        self.t = 0.0
        self.moving = False

    # ---- state helpers
    @property
    def on_ground(self):
        return self.z <= 0 and self.vz <= 0

    def hurtbox(self):
        rel = (-6, 6, -26, 0) if self.crouch and self.on_ground else (-6, 6, -46, 0)
        return wrect(self.x, 1, rel, self.z)

    def attack_rect(self):
        """World rect of the active attack hitbox (or None)."""
        if not self.atk:
            return None
        a = ATTACKS[self.atk]
        t0, t1, _ = a["t"]
        if self.atk != "jkick" and not (t0 <= self.atk_t < t1):
            return None
        return wrect(self.x, self.facing, a["rect"], self.z)

    # ---- update
    def update(self, dt, inp, g):
        self.t += dt
        self.invuln = max(0.0, self.invuln - dt)
        self.used = set()
        if self.dead:
            self.dead_t += dt
            self._air(dt, g)
            self.x += self.kvx * dt
            self.kvx *= 0.94
            return
        if self.victory:
            return
        self.grips = [e for e in self.grips if e.alive and e.state == "latched"]

        if self.hurt_t > 0:
            self.hurt_t -= dt
            self.x += self.kvx * dt
            self.kvx *= 0.9
            self.atk = None
            self._air(dt, g)
            return

        grounded = self.on_ground
        if self.atk:
            self.atk_t += dt
            if self.atk != "jkick" and self.atk_t >= ATTACKS[self.atk]["t"][2]:
                self.atk = None

        # shaking off grabbers
        if self.grips:
            need = 6 + 2 * len(self.grips)
            if inp.dir and inp.dir != self.last_dir:
                self.last_dir = inp.dir
                self.shake += 1
                g.audio.play("shake", 0.6)
                if self.shake >= need:
                    self.shake = 0
                    for e in self.grips:
                        e.shaken_off(self)
                    self.grips = []
                    self.invuln = max(self.invuln, 0.35)
                    g.audio.play("whoosh")
                    g.ring(self.x, GROUND - 22, (255, 255, 200))

        if grounded and self.atk is None:
            self.crouch = bool(inp.down) and not self.grips
            if inp.mx:
                self.facing = 1 if inp.mx > 0 else -1
            mv = 0 if (self.crouch or self.grips) else inp.mx
            self.moving = bool(mv)
            lo, hi = g.player_bounds()
            self.x = clamp(self.x + mv * PLAYER_SPEED * dt, lo, hi)
            if mv:
                self.anim += dt * 1.9
                self.step_t -= dt
                if self.step_t <= 0:
                    self.step_t = 0.28
                    g.dust(self.x - self.facing * 4, GROUND, 1)
            if inp.jump and not self.grips:
                self.vz = JUMP_V
                self.vx = mv * PLAYER_SPEED * 0.9
                self.air_atk = False
                self.used.add("jump")
                g.audio.play("jump")
            elif inp.punch or inp.kick:
                self._start("c" if self.crouch else "", "kick" if inp.kick else "punch", g)
                self.used.update(("punch", "kick"))
        elif grounded:
            self.moving = False
        else:
            self.crouch = False
            if inp.mx:
                self.vx = inp.mx * PLAYER_SPEED * 0.85
            lo, hi = g.player_bounds()
            self.x = clamp(self.x + self.vx * dt, lo, hi)
            if (inp.punch or inp.kick) and not self.air_atk and self.atk is None:
                self.air_atk = True
                self.atk, self.atk_t = "jkick", 0.0
                self.hit_ids = set()
                self.used.update(("punch", "kick"))
                g.audio.play("whoosh")
        self._air(dt, g)

    def _start(self, prefix, kind, g):
        self.atk = prefix + kind
        self.atk_t = 0.0
        self.hit_ids = set()
        g.audio.play("whoosh", 0.7)

    def _air(self, dt, g):
        if self.z > 0 or self.vz > 0:
            self.z += self.vz * dt
            self.vz -= GRAVITY * dt
            if self.z <= 0:
                self.z, self.vz = 0.0, 0.0
                self.vx = 0.0
                if self.atk == "jkick":
                    self.atk = None
                g.audio.play("land", 0.6)
                g.dust(self.x, GROUND, 3)

    # ---- damage
    def take_hit(self, dmg, from_x, g, kb=1.0, stun=0.3):
        if self.invuln > 0 or self.dead or self.victory:
            return False
        self.hp -= dmg
        g.on_player_hit(dmg)
        if self.hp <= 0:
            self.die(from_x, g)
            return True
        self.hurt_t = stun
        self.invuln = 1.0
        self.kvx = sign(self.x - from_x) * 95 * kb
        self.atk = None
        if self.on_ground:
            self.vz = 90 * min(kb, 1.3)
            self.z = 0.01
        return True

    def drain(self, dmg, g):
        if self.dead or self.victory:
            return
        self.hp -= dmg
        g.audio.play("grip", 0.7)
        g.flash_player = 0.12
        if self.hp <= 0:
            self.die(self.x + self.facing, g)

    def die(self, from_x, g):
        self.hp = 0
        self.dead = True
        self.dead_t = 0.0
        self.kvx = sign(self.x - from_x) * 70
        self.vz = 170
        self.z = max(self.z, 0.01)
        self.atk = None
        for e in self.grips:
            e.shaken_off(self)
        self.grips = []
        g.audio.play("die")

    # ---- drawing
    def pose(self):
        if self.dead:
            return ("hurt", 0.0) if self.dead_t < 0.35 else ("dead", 0.0)
        if self.victory:
            return "victory", 0.0
        if self.hurt_t > 0:
            return "hurt", 0.0
        if self.atk:
            a = ATTACKS[self.atk]
            t0, t1, _ = a["t"]
            if self.atk == "jkick":
                return "jkick", 0.0
            base = self.atk[1:] if self.atk[0] == "c" else self.atk
            if self.atk_t < t0:
                return (("ckick_w" if self.atk == "ckick" else "crouch") if self.atk[0] == "c" else base + "_w"), 0.0
            if self.atk_t < t1:
                return self.atk, 0.0
            return ("crouch" if self.atk[0] == "c" else "idle"), 0.0
        if not self.on_ground:
            return "jump", 0.0
        if self.grips:
            return "gripped", 0.0
        if self.crouch:
            return "crouch", 0.0
        if self.moving:
            return "walk", self.anim
        return "idle", self.t * 0.6

    def draw(self, surf, cam, fl=False):
        if self.invuln > 0 and not self.dead and self.hurt_t <= 0 and int(self.t * 20) % 2:
            return
        name, ph = self.pose()
        img, (ax, ay) = gfx.frame("hero", self.char, name, ph % 1.0, self.facing < 0)
        sx = int(self.x - cam)
        sy = int(GROUND - self.z)
        sw = max(6, int(22 - self.z * 0.25))
        sh = pygame.Surface((sw * 2, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), (0, 0, sw * 2, 7))
        surf.blit(sh, (sx - sw, GROUND - 3))
        dead = self.dead and self.dead_t >= 0.35
        pos = (sx - ax, sy - ay)
        surf.blit(img, pos)
        if fl or (self.hurt_t > 0.22):
            surf.blit(gfx.white(img), pos)
        if self.grips:
            gfx.text(surf, "SHAKE!", 10, (sx, sy - 58), (255, 240, 130), outline=True)


# =============================================================================
# Enemies
# =============================================================================
KINDS = dict(
    grab=dict(hp=1, hw=6, h=46, speed=46, pts=200, char="grab"),
    knife=dict(hp=1, hw=6, h=46, speed=54, pts=300, char="knife"),
    imp=dict(hp=1, hw=5, h=29, speed=100, pts=250, char="imp"),
    monk=dict(hp=2, hw=6, h=46, speed=50, pts=450, char="monk"),
    snake=dict(hp=1, hw=13, h=10, speed=40, pts=150, char=None),
)


class Enemy:
    def __init__(self, kind, x, g, facing=1):
        k = KINDS[kind]
        self.kind = kind
        self.x, self.z, self.vz, self.vx = float(x), 0.0, 0.0, 0.0
        self.facing = facing
        fl = g.floor
        self.hp = k["hp"] + (1 if (kind == "grab" and fl >= 2) or (kind in ("knife", "monk") and fl >= 3) else 0)
        self.speed = k["speed"] * (1 + 0.07 * fl) * g.tune["spd"] ** 0.5
        self.char = CHARS.get(k["char"]) if k["char"] else None
        self.alive = True
        self.dying = False
        self.dead_t = 0.0
        self.state = "walk"
        self.t = 0.0
        self.cool = random.uniform(0.6, 1.6)
        self.flash = 0.0
        self.anim = random.random()
        self.stun = 0.0
        self.block_cd = 0.0
        self.blocking = 0.0
        self.atk = None            # dict(rect, dmg)
        self.drain_t = 0.0
        self.flinch = 0.0
        self.var = None
        self.floor = fl
        self.pts = k["pts"]
        self.cap = k

    # ---- geometry
    def hurtbox(self):
        k = self.cap
        return wrect(self.x, 1, (-k["hw"], k["hw"], -k["h"], 0), self.z)

    def attack_rect(self):
        if not self.atk:
            return None
        return wrect(self.x, self.facing, self.atk["rect"], self.z)

    # ---- hit by the player
    def hit(self, dmg, g, p):
        if self.dying or not self.alive:
            return False
        if self.blocking > 0:
            g.audio.play("block")
            g.spark(self.x + self.facing * 8, GROUND - 28)
            return "blocked"
        self.hp -= dmg
        self.flash = 0.1
        if self.hp <= 0:
            self.dying = True
            self.dead_t = 0.0
            self.vx = -self.facing * 130 if p.x < self.x else 130
            self.vx = sign(self.x - p.x) * 140
            self.vz = 160
            self.state = "dying"
            self.atk = None
            for e in list(p.grips):
                if e is self:
                    p.grips.remove(e)
            return "killed"
        self.flinch = 0.22
        self.atk = None
        if self.state in ("windup", "leap", "attack", "latched"):
            if self.state == "latched":
                pass
            else:
                self.state = "walk"
        self.vx = sign(self.x - p.x) * 90
        return "hit"

    def shaken_off(self, p):
        self.state = "stun"
        self.stun = 0.9
        self.vx = sign(self.x - p.x) * 170

    # ---- update
    def update(self, dt, g):
        p = g.player
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.cool -= dt
        self.block_cd = max(0.0, self.block_cd - dt)
        self.blocking = max(0.0, self.blocking - dt)
        if self.dying:
            self.dead_t += dt
            self.x += self.vx * dt
            self.vx *= 0.97
            self.z += self.vz * dt
            self.vz -= 700 * dt
            if self.z < 0:
                self.z, self.vz, self.vx = 0.0, 0.0, 0.0
            if self.dead_t > 0.6:
                self.alive = False
            return
        if self.flinch > 0:
            self.flinch -= dt
            self.x += self.vx * dt
            self.vx *= 0.88
            return
        if self.state == "stun":
            self.stun -= dt
            self.x += self.vx * dt
            self.vx *= 0.88
            if self.stun <= 0:
                self.state = "walk"
            return
        getattr(self, "_" + self.kind)(dt, g, p)

    def _face(self, p):
        self.facing = 1 if p.x > self.x else -1

    def _toward(self, p, dt, mult=1.0):
        self._face(p)
        self.x += self.facing * self.speed * mult * dt
        self.anim += dt * (self.speed / 24.0) * mult * 0.2 + dt * 1.2

    def _maybe_block(self, g, p):
        a = p.attack_rect()
        if a and self.block_cd <= 0 and abs(p.x - self.x) < 44 and self.kind == "monk" and random.random() < 0.012:
            self.blocking = 0.4
            self.block_cd = 1.6

    # -- grabber
    def _grab(self, dt, g, p):
        if self.state == "walk":
            self._toward(p, dt)
            if (abs(self.x - p.x) < 15 and p.z < 8 and not p.dead and len(p.grips) < 3 and p.hurt_t <= 0
                    and p.invuln < 0.5):
                self.state = "latched"
                self.side = -1 if self.x < p.x else 1
                self.drain_t = 0.5
                p.grips.append(self)
                g.audio.play("grip")
        elif self.state == "latched":
            self.facing = -self.side
            self.x = p.x + self.side * 11
            self.drain_t -= dt
            if self.drain_t <= 0:
                self.drain_t = 0.5
                p.drain(1, g)

    # -- knife thrower
    def _knife(self, dt, g, p):
        d = abs(p.x - self.x)
        if self.state == "walk":
            self._face(p)
            lo, hi = g.screen_bounds(self.x)
            if d > 175:
                self.x += self.facing * self.speed * dt
            elif d < 105 and (self.x - self.facing * 20 > lo) and (self.x - self.facing * 20 < hi):
                self.x -= self.facing * self.speed * 0.9 * dt
            self.anim += dt * 1.5
            on = lo <= self.x <= hi and d < 270
            if self.cool <= 0 and on:
                self.state = "windup"
                self.t = 0.0
                crouchy = p.crouch
                self.var = "lo" if (crouchy or random.random() < 0.35) else "hi"
        elif self.state == "windup":
            self._face(p)
            if self.t >= max(0.3, 0.5 - 0.04 * self.floor):
                self.state = "recover"
                self.t = 0.0
                hi = self.var == "hi"
                g.projs.append(Proj("knife", self.x + self.facing * 10, GROUND - (36 if hi else 9),
                                    self.facing * (175 + 12 * self.floor), 6 * g.tune["edmg"], self))
                g.audio.play("knife")
        elif self.state == "recover":
            if self.t > 0.35:
                self.state = "walk"
                self.cool = random.uniform(1.4, 2.5) - 0.12 * self.floor

    # -- imp
    def _imp(self, dt, g, p):
        d = abs(p.x - self.x)
        if self.state == "walk":
            self._toward(p, dt)
            if d < 66 and p.on_ground is not None and self.cool <= 0:
                self.state = "windup"
                self.t = 0.0
        elif self.state == "windup":
            self._face(p)
            if self.t > 0.26:
                self.state = "leap"
                self.vx = self.facing * 175
                self.vz = 175
                self.t = 0.0
                self.atk = dict(rect=(-6, 8, -46, -28), dmg=5 * g.tune["edmg"], lift=0)
                g.audio.play("jump", 0.4)
        elif self.state == "leap":
            self.x += self.vx * dt
            self.z += self.vz * dt
            self.vz -= 640 * dt
            if self.z <= 0:
                self.z, self.vz, self.vx = 0.0, 0.0, 0.0
                self.state = "recover"
                self.t = 0.0
                self.atk = None
        elif self.state == "recover":
            if self.t > 0.45:
                self.state = "walk"
                self.cool = random.uniform(0.3, 0.9)

    # -- monk
    def _monk(self, dt, g, p):
        d = abs(p.x - self.x)
        self._maybe_block(g, p)
        if self.blocking > 0:
            return
        if self.state == "walk":
            self._toward(p, dt, 0.9)
            if d < 40 and self.cool <= 0:
                self.state = "windup"
                self.t = 0.0
                self.var = "lo" if (p.crouch or random.random() < 0.4) else "hi"
        elif self.state == "windup":
            self._face(p)
            if self.t >= 0.42 - 0.03 * self.floor:
                self.state = "attack"
                self.t = 0.0
                rect = (6, 32, -41, -30) if self.var == "hi" else (6, 36, -9, 0)
                self.atk = dict(rect=rect, dmg=6 * g.tune["edmg"], lift=0)
                g.audio.play("whoosh")
        elif self.state == "attack":
            if self.t > 0.17:
                self.atk = None
                self.state = "recover"
                self.t = 0.0
        elif self.state == "recover":
            self.x -= self.facing * 25 * dt
            if self.t > 0.55:
                self.state = "walk"
                self.cool = random.uniform(0.5, 1.2)

    # -- snake
    def _snake(self, dt, g, p):
        self._toward(p, dt)
        self.atk = dict(rect=(-12, 12, -10, 0), dmg=3 * g.tune["edmg"], lift=0, tick=0.7)

    # ---- draw
    def pose(self):
        k = self.kind
        if self.dying:
            return ("hurt", 0.0)
        if self.flinch > 0:
            return ("hurt", 0.0)
        if self.blocking > 0:
            return ("block", 0.0)
        if self.state == "stun":
            return ("stun", 0.0)
        if k == "grab":
            return ("grab", 0.0) if self.state == "latched" else ("walk", self.anim)
        if k == "knife":
            if self.state == "windup":
                return ("throw_hi" if self.var == "hi" else "throw_lo", 0.0)
            if self.state == "recover":
                return ("throw", 0.0)
            return ("walk", self.anim)
        if k == "imp":
            if self.state == "windup":
                return ("crouch", 0.0)
            if self.state == "leap":
                return ("jkick", 0.0)
            if self.state == "recover":
                return ("crouch", 0.0)
            return ("run", self.anim)
        if k == "monk":
            if self.state == "windup":
                return ("punch_w" if self.var == "hi" else "ckick_w", 0.0)
            if self.state == "attack":
                return ("punch" if self.var == "hi" else "ckick", 0.0)
            return ("walk", self.anim)
        return ("idle", 0.0)

    def draw(self, surf, cam):
        sx = int(self.x - cam)
        sy = int(GROUND - self.z)
        if self.kind == "snake":
            frames = gfx.snake_sprites()
            img = frames[int(self.anim * 6) % 4]
            if self.facing > 0:
                img = pygame.transform.flip(img, True, False)
            surf.blit(img, (sx - img.get_width() // 2, GROUND - img.get_height() + 3))
            if self.flash > 0:
                surf.blit(gfx.white(img), (sx - img.get_width() // 2, GROUND - img.get_height() + 3))
            return
        name, ph = self.pose()
        img, (ax, ay) = gfx.frame(self.cap["char"], self.char, name, ph % 1.0, self.facing < 0)
        sw = int(10 + 12 * self.char["scale"])
        sh = pygame.Surface((sw * 2, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 80), (0, 0, sw * 2, 6))
        surf.blit(sh, (sx - sw, GROUND - 3))
        pos = (sx - ax, sy - ay)
        if self.dying and self.dead_t > 0.35:
            img = img.copy()
            img.set_alpha(max(0, 255 - int((self.dead_t - 0.35) / 0.25 * 255)))
        surf.blit(img, pos)
        if self.flash > 0:
            surf.blit(gfx.white(img), pos)
        if self.state == "windup" and self.kind in ("monk", "knife"):
            gfx.text(surf, "!", 12, (sx, sy - 56), (255, 90, 70), outline=True)


# =============================================================================
# Projectiles
# =============================================================================
class Proj:
    """kind: knife | disc | fire | wave | rock."""

    def __init__(self, kind, x, y, vx, dmg, owner=None, **kw):
        self.kind, self.x, self.y, self.vx, self.dmg, self.owner = kind, float(x), float(y), vx, dmg, owner
        self.alive = True
        self.t = 0.0
        self.vy = 0.0
        self.hw, self.hh = {"knife": (7, 2), "disc": (8, 8), "fire": (8, 8), "wave": (7, 8), "rock": (5, 5)}[kind]
        self.destroyable = kind in ("knife", "disc", "fire")
        self.range = kw.get("range", 0)
        self.state = "out"
        self.origin = x
        self.life = kw.get("life", 4.0)
        self.hit = False
        self.kw = kw

    def rect(self):
        return pygame.Rect(int(self.x - self.hw), int(self.y - self.hh), self.hw * 2, self.hh * 2)

    def update(self, dt, g):
        self.t += dt
        self.life -= dt
        if self.kind == "disc":
            b = self.owner
            if self.state == "out":
                self.x += self.vx * dt
                if abs(self.x - self.origin) > self.range:
                    self.state = "back"
                    self.hit = False
            else:
                tx = b.x if b and b.state != "dead" else self.x - 60
                d = tx - self.x
                self.x += sign(d) * abs(self.vx) * 1.05 * dt
                if abs(d) < 10 or self.life < 0:
                    self.alive = False
            if self.life < -2:
                self.alive = False
            return
        self.x += self.vx * dt
        if self.kind == "rock":
            self.y += self.vy * dt
            self.vy += 400 * dt
        lo, hi = g.cam - 30, g.cam + W + 30
        if self.x < lo or self.x > hi or self.life < 0:
            self.alive = False

    def draw(self, surf, cam):
        sx, sy = int(self.x - cam), int(self.y)
        if self.kind == "knife":
            img = gfx.knife_sprite()
            if self.vx < 0:
                img = pygame.transform.flip(img, True, False)
            surf.blit(img, img.get_rect(center=(sx, sy)))
        elif self.kind == "disc":
            img = gfx.disc_sprites()[int(self.t * 24) % 4]
            surf.blit(img, img.get_rect(center=(sx, sy)))
            for k in range(1, 4):
                tr = gfx.soft_circle(5, (200, 220, 255), 60 - k * 14)
                surf.blit(tr, (sx - 5 - int(math.copysign(1, self.vx) * k * 6 * (1 if self.state == "out" else -1)),
                               sy - 5))
        elif self.kind == "fire":
            img = gfx.fireball_sprite(int(self.t * 14))
            surf.blit(gfx.glow(18, (200, 80, 20)), (sx - 18, sy - 18), special_flags=pygame.BLEND_RGB_ADD)
            surf.blit(img, img.get_rect(center=(sx, sy)))
            d = 1 if self.vx > 0 else -1
            for k in range(1, 5):
                tr = gfx.soft_circle(max(1, 6 - k), (255, 140, 50), 120 - k * 24)
                surf.blit(tr, (sx - d * k * 6 - 4, sy - 4))
        elif self.kind == "wave":
            # ground shockwave: rolling dust crest with glow
            d = 1 if self.vx > 0 else -1
            pts = [(sx - d * 14, GROUND), (sx - d * 4, GROUND - 6), (sx + d * 4, GROUND - 14), (sx + d * 9, GROUND - 6),
                   (sx + d * 10, GROUND)]
            pygame.draw.polygon(surf, (236, 214, 170), pts)
            pygame.draw.polygon(surf, (255, 246, 214), [(sx - d * 4, GROUND - 3), (sx + d * 3, GROUND - 11),
                                                        (sx + d * 6, GROUND - 4)])
            pygame.draw.polygon(surf, (150, 110, 80), pts, 1)
            surf.blit(gfx.glow(14, (120, 90, 50)), (sx - 14, GROUND - 22), special_flags=pygame.BLEND_RGB_ADD)
        else:
            pygame.draw.circle(surf, (150, 140, 130), (sx, sy), 4)


# =============================================================================
# Hazards (static, placed along the corridor)
# =============================================================================
class Pot:
    kind = "pot"

    def __init__(self, x):
        self.x = float(x)
        self.state = "idle"          # idle -> warn -> fall -> broken
        self.t = 0.0
        self.y = 0.0
        self.alive = True

    def update(self, dt, g):
        p = g.player
        if self.state == "idle":
            if abs(p.x - self.x) < 130 and self.x > g.cam + 20 and self.x < g.cam + W - 20:
                self.state, self.t = "warn", 0.0
        elif self.state == "warn":
            self.t += dt
            if self.t > 0.95:
                self.state, self.t, self.y = "fall", 0.0, 16.0
        elif self.state == "fall":
            self.y += 560 * dt
            if self.y >= GROUND - 10:
                self.state, self.t = "broken", 0.0
                g.audio.play("break")
                g.debris(self.x, GROUND - 6, (190, 100, 58), 14)
                g.dust(self.x, GROUND, 6)
                r = pygame.Rect(int(self.x - 11), GROUND - 22, 22, 22)
                pr = p.hurtbox()
                if r.colliderect(pr) and p.z < 12:
                    p.take_hit(7 * g.tune["edmg"], self.x, g, kb=1.1)
        elif self.state == "broken":
            self.t += dt
            if self.t > 0.5:
                self.alive = False

    def draw(self, surf, cam):
        sx = int(self.x - cam)
        if self.state == "warn":
            a = 70 + int(60 * abs(math.sin(self.t * 14)))
            sh = pygame.Surface((26, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, a), (0, 0, 26, 7))
            surf.blit(sh, (sx - 13, GROUND - 3))
            if int(self.t * 12) % 2:
                gfx.text(surf, "!", 12, (sx, GROUND - 40), (255, 90, 70), outline=True)
        elif self.state == "fall":
            img = gfx.pot_sprite()
            surf.blit(img, (sx - img.get_width() // 2, int(self.y) - img.get_height()))


class Flame:
    kind = "flame"

    def __init__(self, x, phase=0.0):
        self.x = float(x)
        self.t = phase
        self.alive = True
        self.cycle = 3.4
        self.on = False
        self.warn = False

    def update(self, dt, g):
        self.t += dt
        c = self.t % self.cycle
        self.warn = 1.7 <= c < 2.4
        was = self.on
        self.on = 2.4 <= c < 3.4
        if self.on and not was and self.x > g.cam and self.x < g.cam + W:
            g.audio.play("fire", 0.5)
        if self.on:
            r = pygame.Rect(int(self.x - 9), GROUND - 60, 18, 60)
            if r.colliderect(g.player.hurtbox()):
                g.player.take_hit(6 * g.tune["edmg"], self.x, g, kb=0.9)

    def draw(self, surf, cam):
        sx = int(self.x - cam)
        if sx < -30 or sx > W + 30:
            return
        # grate
        pygame.draw.rect(surf, (36, 30, 34), (sx - 10, GROUND - 2, 20, 5))
        pygame.draw.rect(surf, (90, 70, 60), (sx - 10, GROUND - 2, 20, 5), 1)
        if self.warn:
            k = 0.5 + 0.5 * math.sin(self.t * 30)
            surf.blit(gfx.glow(12, (int(150 * k) + 40, 40, 10)), (sx - 12, GROUND - 12),
                      special_flags=pygame.BLEND_RGB_ADD)
            for i in (-6, 0, 6):
                pygame.draw.line(surf, (255, 150, 60), (sx + i, GROUND - 2), (sx + i, GROUND - 6 - int(k * 5)), 1)
        elif self.on:
            c = self.t % self.cycle - 2.4
            h = int(60 * min(1.0, c / 0.15)) if c < 0.15 else 60 - int(max(0, c - 0.8) * 120)
            for layer, (col, w) in enumerate((((190, 50, 20), 18), ((250, 130, 40), 13), ((255, 220, 120), 7))):
                pts = [(sx - w // 2, GROUND - 1)]
                for k in range(1, 6):
                    yy = GROUND - 1 - h * k / 5
                    off = math.sin(self.t * 20 + k * 1.3 + layer) * (3 - layer * 0.5)
                    pts.append((sx - w // 2 * (1 - k / 7) + off, yy))
                pts.append((sx + off * 0.3, GROUND - 1 - h - 4))
                for k in range(5, 0, -1):
                    yy = GROUND - 1 - h * k / 5
                    off = math.sin(self.t * 20 + k * 1.7 + layer) * (3 - layer * 0.5)
                    pts.append((sx + w // 2 * (1 - k / 7) + off, yy))
                pts.append((sx + w // 2, GROUND - 1))
                pygame.draw.polygon(surf, col, pts)
            surf.blit(gfx.glow(34, (200, 90, 30)), (sx - 34, GROUND - 60), special_flags=pygame.BLEND_RGB_ADD)
