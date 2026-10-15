"""Gunslingers, bullets, cover objects and particles."""
import itertools
import math
import random

import pygame

import gfx
from config import (W, H, HORIZON, PLAYER_MIN_Y, PLAYER_MAX_Y, LEFT_ZONE, RIGHT_ZONE, PLAYER_SPEED,
                    BULLET_SPEED, AIM_ANGLES, CYLINDER, RELOAD_TIME, FIRE_COOLDOWN)

_ids = itertools.count(1)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Gunslinger:
    def __init__(self, side, char):
        self.side = side
        self.facing = 1 if side == 0 else -1
        self.char = char
        self.name = char["name"]
        self.frames = gfx.build_character(char)
        self.geom = gfx.body_geom(char)
        self.max_hp = char.get("hp", 1)
        self.zone = LEFT_ZONE if side == 0 else RIGHT_ZONE
        self.reset()

    def reset(self):
        self.x = 60.0 if self.side == 0 else 340.0
        self.y = 155.0
        self.vx = self.vy = 0.0
        self.ammo = CYLINDER
        self.reload_t = 0.0
        self.cool = 0.0
        self.jam_t = 0.0
        self.shoot_t = 0.0
        self.aim = "straight"
        self.alive = True
        self.moving = False
        self.anim_t = 0.0
        self.step_t = 0.0
        self.dead_t = 0.0
        self.hp = self.max_hp
        self.hp_shown = float(self.max_hp)   # trailing "damage" bar
        self.invuln = 0.0
        self.hurt_t = 0.0

    def update(self, dt, mx, my, speed_mult=1.0):
        events = []
        if self.alive:
            ln = math.hypot(mx, my)
            if ln > 1:
                mx, my = mx / ln, my / ln
            sp = PLAYER_SPEED * speed_mult * (0.6 if self.shoot_t > 0 else 1.0)
            nx = clamp(self.x + mx * sp * dt, *self.zone)
            ny = clamp(self.y + my * sp * dt, self.geom["min_y"], PLAYER_MAX_Y)
            if dt > 0:
                self.vx, self.vy = (nx - self.x) / dt, (ny - self.y) / dt
            self.x, self.y = nx, ny
            self.moving = abs(mx) + abs(my) > 0.15
            if self.moving:
                self.anim_t += dt
                self.step_t -= dt
                if self.step_t <= 0:
                    self.step_t = 0.22
                    events.append("step")
        else:
            self.vx = self.vy = 0.0
            self.dead_t += dt
        self.cool = max(0.0, self.cool - dt)
        self.shoot_t = max(0.0, self.shoot_t - dt)
        self.jam_t = max(0.0, self.jam_t - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.hurt_t = max(0.0, self.hurt_t - dt)
        if self.hp_shown > self.hp:
            self.hp_shown = max(float(self.hp), self.hp_shown - dt * 1.5)
        if self.reload_t > 0:
            self.reload_t -= dt
            if self.reload_t <= 0:
                self.reload_t = 0.0
                self.ammo = CYLINDER
                events.append("reloaded")
        return events

    def can_fire(self):
        return self.alive and self.ammo > 0 and self.reload_t <= 0 and self.cool <= 0 and self.jam_t <= 0

    def fire(self, aim):
        self.ammo -= 1
        self.cool = FIRE_COOLDOWN
        self.shoot_t = 0.22
        self.aim = aim
        if self.ammo <= 0:
            self.reload_t = RELOAD_TIME
        gx, gy = self.gun_pos(aim)
        return Bullet(gx, gy, AIM_ANGLES[aim], self.facing, self.side)

    def gun_pos(self, aim, y=None):
        ox, oy = self.geom["guns"][aim]
        return self.x + ox * self.facing, (self.y if y is None else y) + oy

    @property
    def gun_dy(self):
        """Height of a straight shot relative to the feet."""
        return self.geom["guns"]["straight"][1]

    def hitbox(self):
        dx, dy, w, h = self.geom["hitbox"]
        if self.facing < 0:
            dx = -(dx + w) + 1
        return pygame.Rect(int(self.x) + dx, int(self.y) + dy, w, h)

    def wound(self):
        """Non-lethal hit on a multi-hit boss."""
        self.hp -= 1
        self.invuln = 0.45
        self.hurt_t = 0.3
        self.x = clamp(self.x - 6 * self.facing, *self.zone)

    def frame_name(self):
        if not self.alive:
            return "dead" if self.dead_t > 0.12 else "idle"
        if self.shoot_t > 0:
            return self.aim
        if self.moving:
            return ("walk_a", "idle", "walk_b", "idle")[int(self.anim_t * 8) % 4]
        return "idle"

    def draw(self, surf, ox=0, oy=0):
        img = self.frames[self.frame_name()][0 if self.facing > 0 else 1]
        x, y = int(self.x) + ox, int(self.y) + oy
        g = self.geom
        sw = g["shadow"]
        pygame.draw.ellipse(surf, (0, 0, 0, 70), (x - sw // 2, y - 2, sw, 5))
        if not self.alive and self.dead_t > 0.12:
            surf.blit(img, img.get_rect(midbottom=(x - 3 * self.facing, y + 2)))
            return
        kick = -2 * self.facing if (not self.alive) else 0
        left = x - g["left"][0 if self.facing > 0 else 1]
        pos = (left + kick, y - g["top"])
        surf.blit(img, pos)
        if self.hurt_t > 0 and int(self.hurt_t * 20) % 2 == 0:
            surf.blit(gfx.white_version(img), pos)
        if self.jam_t > 0 and int(self.jam_t * 10) % 2 == 0:
            gfx.text(surf, "?", 12, (x, y - g["top"] - 6), (255, 230, 120), outline=True)


class Bullet:
    def __init__(self, x, y, angle, facing, owner):
        self.id = next(_ids)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * BULLET_SPEED * facing
        self.vy = math.sin(angle) * BULLET_SPEED
        self.owner = owner
        self.alive = True
        self.age = 0.0
        self.bounces = 0
        self.trail = []

    def draw(self, surf, ox=0, oy=0):
        n = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            c = gfx.lerp((120, 60, 20), (255, 200, 90), (i + 1) / max(1, n))
            surf.fill(c, (int(tx) + ox, int(ty) + oy, 1, 1))
        surf.fill((255, 250, 220), (int(self.x) + ox - 1, int(self.y) + oy, 2, 1))


class Obstacle:
    # kind: (hp or None for indestructible, collision rect builder)
    HP = {"cactus": 4, "barrel": 3, "tumble": 1, "wagon": None, "coach": None, "rock": None}

    def __init__(self, kind, x, y, speed=0.0):
        self.kind = kind
        self.x, self.y = float(x), float(y)
        self.max_hp = self.HP[kind]
        self.hp = self.max_hp
        self.vy = float(speed)
        self.vx = 0.0
        self.active = True
        self.flash = 0.0
        self.rot = 0.0
        self.respawn_t = 0.0
        self.sprites = gfx.obstacle_sprite(kind)
        self.rect = pygame.Rect(0, 0, 0, 0)
        if kind == "tumble":
            self._respawn(first=True)
        self._update_rect()

    @property
    def destructible(self):
        return self.max_hp is not None

    def _respawn(self, first=False):
        rnd = random
        self.hp = 1
        self.active = not first or rnd.random() < 0.5
        self.respawn_t = 0.0 if self.active else rnd.uniform(0.5, 3.0)
        d = rnd.choice((-1, 1))
        self.vx = d * rnd.uniform(26, 48)
        self.x = rnd.uniform(60, W - 60) if (first and self.active) else (-8 if d > 0 else W + 8)
        self.y = rnd.uniform(PLAYER_MIN_Y + 4, PLAYER_MAX_Y - 4)
        self.base_y = self.y
        self.hop = rnd.uniform(0, 6)

    def _update_rect(self):
        k, x, y = self.kind, int(self.x), int(self.y)
        if k == "cactus":
            h = max(4, int(34 * self.hp / self.max_hp))
            self.rect = pygame.Rect(x - 7, y - h, 14, h)
        elif k == "wagon":
            self.rect = pygame.Rect(x - 24, y - 31, 48, 30)
        elif k == "coach":
            self.rect = pygame.Rect(x - 20, y - 34, 40, 33)
        elif k == "barrel":
            self.rect = pygame.Rect(x - 6, y - 15, 12, 15)
        elif k == "rock":
            self.rect = pygame.Rect(x - 9, y - 11, 18, 11)
        else:
            self.rect = pygame.Rect(x - 5, y - 11, 10, 10)

    def damage(self):
        """Returns True if the object was destroyed."""
        self.flash = 0.08
        if not self.destructible:
            return False
        self.hp -= 1
        if self.hp <= 0:
            if self.kind == "tumble":
                self._respawn()
                self.active = False
                self.respawn_t = random.uniform(1.5, 4.0)
            else:
                self.active = False
            return True
        self._update_rect()
        return False

    def update(self, dt):
        self.flash = max(0.0, self.flash - dt)
        if self.kind == "tumble":
            if not self.active:
                self.respawn_t -= dt
                if self.respawn_t <= 0:
                    self.active = True
                return
            self.x += self.vx * dt
            self.hop += dt * 5
            self.y = self.base_y - abs(math.sin(self.hop)) * 5
            self.rot += self.vx * dt * 6
            if self.x < -16 or self.x > W + 16:
                self._respawn()
                self.active = False
                self.respawn_t = random.uniform(0.5, 2.5)
        elif self.vy:
            self.y += self.vy * dt
            lo, hi = PLAYER_MIN_Y + 20, PLAYER_MAX_Y
            if self.y < lo or self.y > hi:
                self.y = clamp(self.y, lo, hi)
                self.vy = -self.vy
        self._update_rect()

    @property
    def sort_y(self):
        return self.base_y if self.kind == "tumble" else self.y

    def draw(self, surf, ox=0, oy=0):
        if not self.active:
            return
        x, y = int(self.x) + ox, int(self.y) + oy
        if self.kind == "tumble":
            img = self.sprites[int(self.rot // 45) % 8]
            sh_w = 10
            pygame.draw.ellipse(surf, (0, 0, 0, 60), (x - 5, int(self.base_y) + oy - 3, sh_w, 4))
            surf.blit(img, img.get_rect(midbottom=(x, y)))
            return
        img = self.sprites
        w, h = img.get_size()
        pygame.draw.ellipse(surf, (0, 0, 0, 70), (x - w // 2 + 1, y - 3, w - 2, 6))
        if self.kind == "cactus" and self.hp < self.max_hp:
            vis = max(5, int(h * self.hp / self.max_hp))
            area = pygame.Rect(0, h - vis, w, vis)
            surf.blit(img, (x - w // 2, y - vis + 1), area)
            # jagged broken top
            for i in range(3):
                surf.fill((210, 230, 150), (x - 3 + i * 2, y - vis + 1 + (i % 2), 2, 1))
        else:
            surf.blit(img, (x - w // 2, y - h + 1))
        if self.flash > 0:
            white = gfx.white_version(img)
            if self.kind == "cactus" and self.hp < self.max_hp:
                vis = max(5, int(h * self.hp / self.max_hp))
                surf.blit(white, (x - w // 2, y - vis + 1), pygame.Rect(0, h - vis, w, vis))
            else:
                surf.blit(white, (x - w // 2, y - h + 1))


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "size", "grav", "kind", "drag", "img", "rot",
                 "vr", "floor")

    def __init__(self, x, y, vx, vy, life, color=(255, 255, 255), size=1, grav=0.0, kind="px", drag=0.0,
                 img=None, vr=0.0, floor=None):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color, self.size, self.grav, self.kind, self.drag = color, size, grav, kind, drag
        self.img, self.rot, self.vr, self.floor = img, 0.0, vr, floor

    def update(self, dt):
        self.vy += self.grav * dt
        if self.drag:
            k = max(0.0, 1 - self.drag * dt)
            self.vx *= k
            self.vy *= k
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rot += self.vr * dt
        if self.floor is not None and self.y >= self.floor:
            self.y = self.floor
            self.vx *= 0.3
            self.vy = 0.0
            self.vr = 0.0
            self.grav = 0.0
        self.life -= dt
        return self.life > 0

    def draw(self, surf, ox=0, oy=0):
        x, y = int(self.x) + ox, int(self.y) + oy
        k = self.kind
        if k == "px":
            surf.fill(self.color, (x, y, self.size, self.size))
        elif k == "smoke":
            t = self.life / self.max
            r = int(self.size + (1 - t) * 4)
            a = int(150 * t) // 16 * 16
            if a > 0:
                c = gfx.soft_circle(r, self.color, a)
                surf.blit(c, (x - r, y - r))
        elif k == "img":
            img = pygame.transform.rotate(self.img, int(self.rot) // 15 * 15) if self.rot else self.img
            surf.blit(img, img.get_rect(center=(x, y)))


class FloatText:
    def __init__(self, x, y, s, color=(255, 230, 140), life=1.0, size=12):
        self.x, self.y, self.s, self.color, self.life, self.size = x, y, s, color, life, size

    def update(self, dt):
        self.y -= 14 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        if self.life > 0.15 or int(self.life * 30) % 2:
            gfx.text(surf, self.s, self.size, (int(self.x), int(self.y)), self.color, outline=True)
