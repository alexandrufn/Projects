"""CPU gunslinger. Difficulty comes from the per-level parameters in config.LEVELS.

The brain sees the world through a delayed, noisy "perception" snapshot, plans
shots by simulating bullet paths (including fence ricochets on higher levels),
dodges incoming fire it notices in time, and hides behind cover to reload.
"""
import math
import random

from config import (BULLET_MIN_Y, BULLET_MAX_Y, BULLET_SPEED, AIM_ANGLES,
                    PLAYER_MIN_Y, PLAYER_MAX_Y, PLAYER_SPEED)


def trace(x, y, vx, vy, obstacles, target_x, max_bounces, dt=1 / 120):
    """Simulate a bullet until it reaches target_x. Returns (y, time) or None if blocked."""
    t = 0.0
    bounces = 0
    dirx = 1 if vx > 0 else -1
    rects = [o.rect for o in obstacles if o.active]
    while (target_x - x) * dirx > 0:
        x += vx * dt
        y += vy * dt
        t += dt
        if y < BULLET_MIN_Y:
            y = 2 * BULLET_MIN_Y - y
            vy = -vy
            bounces += 1
        elif y > BULLET_MAX_Y:
            y = 2 * BULLET_MAX_Y - y
            vy = -vy
            bounces += 1
        if bounces > max_bounces or t > 3:
            return None
        ix, iy = int(x), int(y)
        for r in rects:
            if r.collidepoint(ix, iy):
                return None
    return y, t


def line_clear(x0, x1, y, obstacles):
    lo, hi = min(x0, x1), max(x0, x1)
    for o in obstacles:
        if not o.active:
            continue
        r = o.rect
        if r.top <= y <= r.bottom and r.right >= lo and r.left <= hi:
            return False
    return True


class CpuBrain:
    def __init__(self, cfg, me, foe):
        self.base = cfg
        self.cfg = dict(cfg)
        self.me = me
        self.foe = foe
        self.rnd = random.Random()
        self.reset()

    def reset(self):
        self.cfg = dict(self.base)
        self.perceive_t = 0.0
        self.seen = (self.foe.x, self.foe.y, 0.0)
        self.err = 0.0
        self.lock_t = 0.0
        self.last_shot = 99.0
        self.dodge_t = 0.0
        self.dodge_dir = 0
        self.judged = set()
        self.wander_t = 0.0
        self.goal_x = self.me.x
        self.draw_delay = None
        self.think_t = 0.0
        self.best_aim = None
        self.clock = self.rnd.uniform(0, 10)

    def enrage(self):
        """A wounded boss gets faster and meaner for the rest of the round."""
        c = self.cfg
        c["reaction"] *= 0.85
        c["interval"] *= 0.8
        c["aggression"] = min(1.0, c["aggression"] + 0.2)
        c["strafe"] = min(0.8, c["strafe"] + 0.15)
        self.last_shot = c["interval"]

    def _goal_x(self):
        lo, hi = self.me.zone
        near, far = (hi, lo) if self.me.side == 0 else (lo, hi)
        a = self.cfg["aggression"]
        u = self.rnd.uniform(a * 0.6, min(1.0, a + 0.35))
        return far + (near - far) * u

    def update(self, dt, game):
        cfg, me, foe = self.cfg, self.me, self.foe
        if not me.alive:
            return 0.0, 0.0, None
        self.clock += dt
        fighting = game.state == "fight"

        # ---- delayed, noisy perception of the opponent
        self.perceive_t -= dt
        if self.perceive_t <= 0:
            self.perceive_t = cfg["reaction"] * 0.5 * self.rnd.uniform(0.7, 1.3)
            self.seen = (foe.x, foe.y, foe.vy)
            self.err = self.rnd.gauss(0, cfg["aim_err"])
        fx, fy, fvy = self.seen
        fy += self.err

        # ---- notice incoming bullets and maybe dodge
        self.dodge_t -= dt
        for b in game.bullets:
            if b.owner == me.side or b.id in self.judged or b.age < cfg["reaction"] * 0.6:
                continue
            self.judged.add(b.id)
            if self.rnd.random() > cfg["dodge"]:
                continue
            res = trace(b.x, b.y, b.vx, b.vy, game.obstacles, me.x, 2)
            if res is None:
                continue
            hy, t = res
            box = me.hitbox()
            chest = box.centery
            if abs(hy - chest) < box.h / 2 + 5 and t < 1.2:
                d = 1 if hy < chest else -1
                if me.y > PLAYER_MAX_Y - 12 and d > 0:
                    d = -1
                if me.y < me.geom["min_y"] + 12 and d < 0:
                    d = 1
                self.dodge_dir = d
                self.dodge_t = 0.2 + 20 / (PLAYER_SPEED * cfg["speed"])
        if len(self.judged) > 300:
            alive = {b.id for b in game.bullets}
            self.judged &= alive

        # ---- shooting
        aim = None
        self.last_shot += dt
        if fighting:
            if self.draw_delay is None:
                self.draw_delay = cfg["draw"] * self.rnd.uniform(0.8, 1.25)
            self.draw_delay -= dt
        self.think_t -= dt
        if self.think_t <= 0:
            self.think_t = 0.08
            self.best_aim = self._find_shot(game, fx, fy, fvy)
        if fighting and self.best_aim and self.draw_delay <= 0 and me.can_fire():
            self.lock_t += dt
            if self.lock_t >= cfg["reaction"] * 0.4 and self.last_shot >= cfg["interval"]:
                aim = self.best_aim
                self.last_shot = 0.0
                self.lock_t = 0.0
        else:
            self.lock_t = max(0.0, self.lock_t - dt * 0.5)

        # ---- movement
        mx = my = 0.0
        if self.dodge_t > 0:
            my = float(self.dodge_dir)
        else:
            ty = self._choose_y(game, fx, fy)
            dy = ty - me.y
            if abs(dy) > 2:
                my = max(-1.0, min(1.0, dy / 10))
            if cfg["strafe"] > 0 and fighting:
                my += math.sin(self.clock * 3.1) * cfg["strafe"]
        self.wander_t -= dt
        if self.wander_t <= 0:
            self.wander_t = self.rnd.uniform(1.5, 3.5)
            self.goal_x = self._goal_x()
        dx = self.goal_x - me.x
        if abs(dx) > 3:
            mx = 0.7 if dx > 0 else -0.7
        return mx, my, aim

    def _foe_mid(self):
        _, dy, _, h = self.foe.geom["hitbox"]
        return dy + h / 2

    def _find_shot(self, game, fx, fy, fvy):
        me, cfg = self.me, self.cfg
        max_b = 1 if cfg["ricochet"] else 0
        best, bestd = None, 1e9
        for aim in ("straight", "up", "down"):
            gx, gy = me.gun_pos(aim)
            ang = AIM_ANGLES[aim]
            vx = math.cos(ang) * BULLET_SPEED * me.facing
            vy = math.sin(ang) * BULLET_SPEED
            res = trace(gx, gy, vx, vy, game.obstacles, fx, max_b)
            if res is None:
                continue
            hy, t = res
            target = fy + self._foe_mid() + (fvy * t if cfg["predict"] else 0.0)
            target = max(BULLET_MIN_Y, min(BULLET_MAX_Y, target))
            d = abs(hy - target)
            if d < 7 and d < bestd:
                best, bestd = aim, d
        return best

    def _choose_y(self, game, fx, fy):
        me, cfg = self.me, self.cfg
        clampy = lambda v: max(me.geom["min_y"], min(PLAYER_MAX_Y, v))
        if cfg["cover"] and me.reload_t > 0:
            covers = [o for o in game.obstacles if o.active and o.kind != "tumble" and o.rect.h >= 10]
            if covers:
                o = min(covers, key=lambda o: abs(o.rect.centery - me.gun_dy - me.y))
                return clampy(o.rect.centery - me.gun_dy)
        ox = me.geom["guns"]["straight"][0] * me.facing
        desired = fy + self._foe_mid() - me.gun_dy      # put my straight shot on the foe's chest
        for off in (0, 8, -8, 16, -16, 24, -24, 32, -32):
            y = clampy(desired + off)
            if line_clear(me.x + ox, fx, y + me.gun_dy, game.obstacles):
                return y
        return clampy(desired)
