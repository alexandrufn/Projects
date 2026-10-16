"""Gameplay objects: the player, enemies, bosses, bullets, pickups and effects.

Combat objects live in screen coordinates; only obstacles, barrels and pickups sit in the
scrolling world (their y is a world y, converted with `scene.sy(wy)`).
"""
import math

import pygame

from config import (W, H, OY, PLAYER_SPEED, HEROES, WEAPONS, WEAPON_TIME, INVULN_HIT)

MIN_X, MAX_X = 10, W - 10
MIN_Y, MAX_Y = OY + 18, H - 12


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "dmg", "pierce", "life", "friendly", "hit", "r")

    def __init__(self, x, y, vx, vy, dmg=1, pierce=False, life=3.0, friendly=True, r=2):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.dmg, self.pierce, self.life, self.friendly, self.r = dmg, pierce, life, friendly, r
        self.hit = set()

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def alive(self):
        return self.life > 0 and -12 < self.x < W + 12 and OY - 12 < self.y < H + 12


class Dynamite:
    """A lobbed stick: flies to (tx, ty), then explodes."""

    def __init__(self, x, y, tx, ty, flight=1.05):
        self.x0, self.y0, self.tx, self.ty = x, y, tx, ty
        self.flight = flight
        self.t = 0.0
        self.x, self.y = x, y
        self.height = 0.0

    def update(self, dt):
        self.t += dt
        k = min(1.0, self.t / self.flight)
        self.x = self.x0 + (self.tx - self.x0) * k
        self.y = self.y0 + (self.ty - self.y0) * k
        self.height = math.sin(k * math.pi) * 34
        return self.t >= self.flight


class Explosion:
    def __init__(self, x, y, radius, dmg_player=1, dmg_enemy=3, harms_enemies=True):
        self.x, self.y, self.radius = x, y, radius
        self.t = 0.0
        self.life = 0.45
        self.dmg_player, self.dmg_enemy = dmg_player, dmg_enemy
        self.harms_enemies = harms_enemies
        self.applied = False


class Puff:
    """Gun smoke and dust."""
    __slots__ = ("x", "y", "vx", "vy", "age", "life", "size", "color")

    def __init__(self, x, y, vx, vy, life, size, color=(220, 218, 214)):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.age, self.life, self.size, self.color = 0.0, life, size, color

    def update(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.96
        self.vy *= 0.96
        return self.age < self.life


class Item:
    def __init__(self, kind, x, wy):
        self.kind, self.x, self.wy = kind, x, wy
        self.t = 0.0


class Barrel:
    def __init__(self, x, wy):
        self.x, self.wy = x, wy
        self.hp = 2
        self.flash = 0.0

    def rect(self):
        return pygame.Rect(int(self.x), int(self.wy), 14, 14)


# ----------------------------------------------------------------------------
# The player
# ----------------------------------------------------------------------------
class Player:
    def __init__(self, hero="hank"):
        self.hero = hero
        self.stats = HEROES[hero]
        self.max_hp = self.stats["max_hp"]
        self.reset(full=True)

    def reset(self, full=False):
        self.x, self.y = W / 2, H - 40
        self.hp = self.stats["hp"]
        self.invuln = 0.0
        self.cool = 0.0
        self.anim = 0.0
        self.aim = 0
        self.weapon, self.wtime = "revolver", 0.0
        self.boots = False
        if full:
            self.bombs = self.stats["bombs"]
        self.dead = False

    @property
    def speed(self):
        return PLAYER_SPEED * self.stats["speed"] * (1.3 if self.boots else 1.0)

    def update(self, dt, inp, blockers):
        self.invuln = max(0.0, self.invuln - dt)
        self.cool = max(0.0, self.cool - dt)
        if self.wtime > 0:
            self.wtime -= dt
            if self.wtime <= 0:
                self.weapon = "revolver"
        dx, dy = inp.dx, inp.dy
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        if dx or dy:
            self.anim += dt * 9
        # move one axis at a time so we slide along solid objects
        nx = clamp(self.x + dx * self.speed * dt, MIN_X, MAX_X)
        if not self._blocked(nx, self.y, blockers):
            self.x = nx
        ny = clamp(self.y + dy * self.speed * dt, MIN_Y, MAX_Y)
        if not self._blocked(self.x, ny, blockers):
            self.y = ny
        self.aim = -2 if inp.fire_l and not inp.fire_r else 2 if inp.fire_r and not inp.fire_l else 0

    def _blocked(self, x, y, blockers):
        r = pygame.Rect(int(x - 5), int(y - 6), 10, 8)
        return any(r.colliderect(b) for b in blockers)

    def rect(self):
        return pygame.Rect(int(self.x - 4), int(self.y - 9), 8, 14)

    def shoot(self, inp):
        """Returns (bullets, sound name) for this frame, or ([], None) while cooling down."""
        dirs = []
        if inp.fire_f:
            dirs.append((0.0, -1.0))
        if inp.fire_l:
            dirs.append((-0.5, -0.866))
        if inp.fire_r:
            dirs.append((0.5, -0.866))
        if inp.mouse_fire:
            mx, my = inp.mouse_pos
            ang = math.atan2(my - (self.y - 8), mx - self.x)
            dirs.append((math.cos(ang), math.sin(ang)))
        if not dirs or self.cool > 0:
            return [], None
        w = WEAPONS[self.weapon]
        self.cool = w["cd"] * self.stats["cd"]
        out = []
        for dx, dy in dirs:
            base = math.atan2(dy, dx)
            n = w["pellets"]
            for i in range(n):
                a = base + (0 if n == 1 else (i / (n - 1) - 0.5) * w["spread"])
                out.append(Bullet(self.x + 2 * math.cos(a) + (self.aim and self.aim * 0.5), self.y - 10 + 2 * math.sin(a),
                                  math.cos(a) * w["speed"], math.sin(a) * w["speed"], w["dmg"], w["pierce"], w["life"]))
        return out, self.weapon if self.weapon != "revolver" else "shot"

    def hurt(self):
        if self.invuln > 0 or self.dead:
            return False
        self.hp -= 1
        self.invuln = INVULN_HIT
        if self.hp <= 0:
            self.dead = True
        return True


# ----------------------------------------------------------------------------
# Enemies
# ----------------------------------------------------------------------------
ENEMY_STATS = {
    "outlaw": dict(hp=1, score=100, radius=8),
    "gunman": dict(hp=2, score=200, radius=8),
    "dynamite": dict(hp=1, score=200, radius=8),
    "rider": dict(hp=2, score=250, radius=11),
}


class Enemy:
    def __init__(self, kind, x, y, ctx):
        st = ENEMY_STATS[kind]
        self.kind, self.x, self.y = kind, x, y
        self.hp, self.score, self.radius = st["hp"], st["score"], st["radius"]
        self.t = ctx.rng.random() * 3
        self.age = 0.0
        self.vx = self.vy = 0.0
        self.flash = 0.0
        self.anim = ctx.rng.random() * 4
        self.state = "walk"
        self.shoot_t = ctx.rng.uniform(0.8, 2.2)
        self.burst = 0
        self.burst_t = 0.0
        self.target_y = ctx.rng.randint(OY + 40, OY + 110)
        self.leave_t = ctx.rng.uniform(5.0, 8.0)
        self.contact = kind == "rider"
        if kind == "rider":
            self.vy = 175.0
            self.aim_x = ctx.player.x + ctx.rng.uniform(-30, 30)
            self.vx = clamp((self.aim_x - x) / 1.3, -90, 90)
        self.dead = False

    @property
    def cy(self):
        return self.y - 10

    def update(self, dt, ctx):
        self.age += dt
        self.t += dt
        self.anim += dt * 7
        self.flash = max(0.0, self.flash - dt)
        p = ctx.player
        k = self.kind
        if k == "outlaw":
            self.y += (36 + 8 * math.sin(self.t)) * dt
            self.x += math.sin(self.t * 1.7) * 20 * dt + clamp(p.x - self.x, -1, 1) * 8 * dt
            self.shoot_t -= dt
            if self.shoot_t <= 0 and OY + 8 < self.y < H - 40:
                self.shoot_t = ctx.rng.uniform(1.8, 3.2)
                ctx.enemy_shot(self.x, self.y + 4, ctx.aim_at(self.x, self.y, p, spread=0.14), 80)
        elif k == "gunman":
            if self.state == "walk":
                self.y += 52 * dt
                if self.y >= self.target_y:
                    self.state = "fire"
            elif self.state == "fire":
                self.x += math.sin(self.t * 0.9) * 10 * dt
                self.leave_t -= dt
                self.shoot_t -= dt
                if self.burst > 0:
                    self.burst_t -= dt
                    if self.burst_t <= 0:
                        self.burst -= 1
                        self.burst_t = 0.14
                        ctx.enemy_shot(self.x, self.y + 4, ctx.aim_at(self.x, self.y, p, spread=0.08), 118)
                elif self.shoot_t <= 0:
                    self.shoot_t = ctx.rng.uniform(1.3, 2.0)
                    self.burst, self.burst_t = 3, 0.0
                if self.leave_t <= 0:
                    self.state = "leave"
            else:
                self.y -= 70 * dt
                if self.y < OY - 20:
                    self.dead = True
        elif k == "dynamite":
            if self.state == "walk":
                self.y += 46 * dt
                if self.y >= self.target_y - 30:
                    self.state = "throw"
                    self.shoot_t = 0.6
            elif self.state == "throw":
                self.shoot_t -= dt
                self.leave_t -= dt
                if self.shoot_t <= 0:
                    self.shoot_t = ctx.rng.uniform(2.1, 2.8)
                    ctx.throw_dynamite(self.x, self.y, p.x + ctx.rng.uniform(-14, 14), p.y + ctx.rng.uniform(-10, 10))
                if self.leave_t <= 0:
                    self.state = "leave"
            else:
                self.y -= 70 * dt
                if self.y < OY - 20:
                    self.dead = True
        elif k == "rider":
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.age > 1.3:
                self.vx *= 0.97
        if self.y > H + 40 or self.x < -40 or self.x > W + 40:
            self.dead = True


# ----------------------------------------------------------------------------
# Bosses
# ----------------------------------------------------------------------------
class Boss:
    radius = 17

    def __init__(self, kind, hp, ctx):
        self.kind = kind
        self.hp = self.max_hp = hp
        self.x, self.y = W / 2, OY - 40
        self.t = 0.0
        self.flash = 0.0
        self.anim = 0.0
        self.state = "enter"
        self.timers = {}
        self.angle = 0.0
        self.dash_from = (self.x, self.y)
        self.dead = False
        self.dying = 0.0
        self.last_spawn = 0.0

    @property
    def cy(self):
        return self.y

    # --- helpers
    def _every(self, name, period, ctx, fn):
        t = self.timers.get(name, period) - ctx.dt
        if t <= 0:
            t += period
            fn()
        self.timers[name] = t

    def _ring(self, ctx, n, speed, offset=0.0):
        for i in range(n):
            ctx.enemy_shot(self.x, self.y + 10, offset + i * math.tau / n, speed)

    def _fan(self, ctx, n, spread, speed, aim=None):
        base = math.pi / 2 if aim is None else aim
        for i in range(n):
            ctx.enemy_shot(self.x, self.y + 12, base + (i / max(1, n - 1) - 0.5) * spread, speed)

    # --- update
    def update(self, dt, ctx):
        self.t += dt
        self.anim += dt * 6
        self.flash = max(0.0, self.flash - dt)
        ctx.dt = dt
        p = ctx.player
        if self.dying > 0:
            self.dying += dt
            return
        if self.state == "enter":
            self.y += 50 * dt
            if self.y >= OY + 58:
                self.state = "fight"
                self.t = 0.0
            return
        frac = self.hp / self.max_hp
        rage = 1.0 + (1.0 - frac) * 0.6
        getattr(self, "_" + self.kind)(dt, ctx, p, frac, rage)
        self.x = clamp(self.x, 30, W - 30)

    def _jack(self, dt, ctx, p, frac, rage):
        self.x = W / 2 + math.sin(self.t * 0.8 * rage) * 96
        self.y = OY + 58 + math.sin(self.t * 1.3) * 10
        ctx.dt = dt
        self._every("fan", 1.5 / rage, ctx, lambda: self._fan(ctx, 3, 0.5, 110, ctx.aim_at(self.x, self.y, p)))
        self._every("ring", 4.2 / rage, ctx, lambda: self._ring(ctx, 10, 70, self.t))
        if frac < 0.5:
            self._every("add", 7.0, ctx, lambda: ctx.spawn_enemy("outlaw", self.x, self.y + 20))

    def _lola(self, dt, ctx, p, frac, rage):
        ctx.dt = dt
        s = self.state
        if s == "fight":
            self.x += clamp(p.x - self.x, -1, 1) * 60 * rage * dt
            self.y += (OY + 56 - self.y) * min(1, dt * 3)
            self._every("fan", 1.1 / rage, ctx, lambda: self._fan(ctx, 5, 0.9, 105))
            self.timers["dash"] = self.timers.get("dash", 4.0 / rage) - dt
            if self.timers["dash"] <= 0:
                self.timers["dash"] = 4.0 / rage
                self.state = "windup"
                self.timers["w"] = 0.6
        elif s == "windup":
            self.timers["w"] -= dt
            self.x += math.sin(self.t * 60) * 0.8
            if self.timers["w"] <= 0:
                self.state = "dash"
                self.dash_to = (clamp(p.x, 40, W - 40), min(H - 70, p.y - 30))
        elif s == "dash":
            dx, dy = self.dash_to[0] - self.x, self.dash_to[1] - self.y
            d = math.hypot(dx, dy)
            if d < 6:
                self.state = "return"
                self._ring(ctx, 12, 80)
            else:
                self.x += dx / d * 230 * dt
                self.y += dy / d * 230 * dt
        else:
            self.y -= 120 * dt
            if self.y <= OY + 56:
                self.state = "fight"

    def _mike(self, dt, ctx, p, frac, rage):
        ctx.dt = dt
        self.x = W / 2 + math.sin(self.t * 0.35) * 60
        self.y = OY + 56
        phase = int(self.t / 5.0) % 3
        if phase in (0, 1):
            self.angle += (3.0 if phase == 0 else -3.4) * dt * rage
            self._every("gat", 0.09 / rage, ctx,
                        lambda: ctx.enemy_shot(self.x, self.y + 12, math.pi / 2 + math.sin(self.angle) * 1.15, 120))
            if frac < 0.6:
                self._every("gat2", 0.18, ctx,
                            lambda: ctx.enemy_shot(self.x, self.y + 12, math.pi / 2 - math.sin(self.angle) * 1.15, 95))
        else:
            self._every("burst", 0.9, ctx, lambda: self._fan(ctx, 7, 1.6, 100, ctx.aim_at(self.x, self.y, p)))
        self._every("add", 6.5 / rage, ctx, lambda: (ctx.spawn_enemy("outlaw", 70, OY - 6),
                                                     ctx.spawn_enemy("outlaw", W - 70, OY - 6)))

    def _cobra(self, dt, ctx, p, frac, rage):
        ctx.dt = dt
        self.x = W / 2 + math.sin(self.t * 0.95 * rage) * 104
        self.y = OY + 54 + math.sin(self.t * 2.1) * 8
        self._every("dyn", 2.6 / rage, ctx, lambda: [
            ctx.throw_dynamite(self.x, self.y + 10, clamp(p.x + dx, 16, W - 16), clamp(p.y + dy, MIN_Y, MAX_Y))
            for dx, dy in ((0, 0), (-46, -10), (46, 10))])
        self._every("fan", 1.9 / rage, ctx, lambda: self._fan(ctx, 3, 0.6, 105, ctx.aim_at(self.x, self.y, p)))
        self._every("ride", 7.0 / rage, ctx, lambda: [ctx.spawn_enemy("rider", x, OY - 14) for x in (50, 270)])

    def _diablo(self, dt, ctx, p, frac, rage):
        ctx.dt = dt
        self.x = W / 2 + math.sin(self.t * 0.9) * 100
        self.y = OY + 56 + math.sin(self.t * 1.7) * 14
        self._every("aim", 1.2 / rage, ctx, lambda: self._fan(ctx, 5, 0.7, 118, ctx.aim_at(self.x, self.y, p)))
        if frac < 0.75:
            self.angle += 2.2 * dt
            self._every("spiral", 0.14 / rage, ctx,
                        lambda: [ctx.enemy_shot(self.x, self.y + 10, self.angle + i * math.pi, 82) for i in range(2)])
        if frac < 0.5:
            self._every("dyn", 3.0, ctx, lambda: ctx.throw_dynamite(self.x, self.y + 10, p.x, p.y))
            self._every("ring", 3.6, ctx, lambda: self._ring(ctx, 14, 74, self.t))
        if frac < 0.3:
            self._every("ride", 6.0, ctx, lambda: ctx.spawn_enemy("rider", clamp(p.x, 40, W - 40), OY - 14))
            self._every("add", 5.0, ctx, lambda: ctx.spawn_enemy("gunman", ctx.rng.randint(40, W - 40), OY - 8))
