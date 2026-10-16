"""Characters: Harry, the hens and the big bird."""
import math
import random

import pygame

from config import (W, OY, TILE, FLOOR_ROWS, CAGE_CENTER, PLAYER_SPEED, CLIMB_SPEED, GRAVITY, JUMP_V,
                    bird_speed)


def _sign(v):
    return (v > 0) - (v < 0)


class Player:
    def __init__(self, level):
        self.reset(level)

    def reset(self, level):
        self.x, self.y = level.spawn
        self.vx = self.vy = 0.0
        self.jump_vx = 0.0
        self.state = "ground"          # ground | air | ladder
        self.facing = 1
        self.anim = 0.0
        self.span = (0, 0)

    def rect(self):
        return pygame.Rect(int(self.x - 4), int(self.y - 16), 8, 16)

    def center(self):
        return self.x, self.y - 9

    # ------------------------------------------------------------------ update
    def update(self, dt, inp, level, audio=None):
        if self.state == "ladder":
            dy = (inp.down - inp.up) * CLIMB_SPEED * dt
            self.y += dy
            if dy:
                self.anim += dt * 8
            top, bot = self.span
            if self.y <= top:
                self.y, self.state = top, "ground"
            elif self.y >= bot:
                self.y, self.state = bot, "ground"
            return

        if self.state == "ground":
            dirx = inp.right - inp.left
            self.vx = dirx * PLAYER_SPEED
            if dirx:
                self.facing = dirx
                self.anim += dt * 9
            self.x = max(8.0, min(W - 8.0, self.x + self.vx * dt))
            if (inp.up or inp.down) and self._grab(level, inp):
                return
            if inp.jump_pressed:
                self.vy = -JUMP_V
                self.jump_vx = self.vx
                self.state = "air"
                if audio:
                    audio.play("jump")
            elif not level.standing(self.x, self.y):
                self.vy = 0.0
                self.jump_vx = self.vx
                self.state = "air"
            return

        # airborne
        self.vy += GRAVITY * dt
        nx = max(8.0, min(W - 8.0, self.x + self.jump_vx * dt))
        ny = self.y + self.vy * dt
        if (inp.up or inp.down) and self._grab(level, inp):
            return
        if self.vy > 0:
            for r in FLOOR_ROWS:
                yt = OY + r * TILE
                if self.y <= yt + 1e-6 and ny >= yt and level.standing(nx, yt):
                    self.x, self.y, self.vy, self.state = nx, float(yt), 0.0, "ground"
                    return
        self.x, self.y = nx, ny

    def _grab(self, level, inp):
        col = int(self.x // TILE)
        cx = col * TILE + TILE / 2
        if abs(self.x - cx) > 6:
            return False
        row_up = int((self.y - 1 - OY) // TILE)
        row_dn = int((self.y + 1 - OY) // TILE)
        row = None
        if inp.up and (row_up, col) in level.ladders:
            row = row_up
        elif inp.down and (row_dn, col) in level.ladders:
            row = row_dn
        if row is None:
            return False
        self.x, self.vy, self.state = cx, 0.0, "ladder"
        self.span = level.ladder_span(col, row)
        return True

    def frame(self):
        if self.state == "ladder":
            return "climb%d" % (int(self.anim) % 2)
        if self.state == "air":
            return "jump"
        if self.vx:
            return ("walk0", "idle", "walk1", "idle")[int(self.anim) % 4]
        return "idle"


class Hen:
    def __init__(self, x, y, speed, rng):
        self.x, self.y = x, y
        self.speed = speed
        self.rng = rng
        self.dir = rng.choice((-1, 1))
        self.state = "walk"            # walk | climb | eat
        self.timer = 0.0
        self.anim = rng.random() * 4
        self.target = y
        self.last_col = None
        self.start = (x, y)

    def reset(self):
        self.x, self.y = self.start
        self.state, self.timer, self.last_col = "walk", 0.0, None

    def rect(self):
        return pygame.Rect(int(self.x - 6), int(self.y - 12), 12, 12)

    def update(self, dt, level, player):
        if self.state == "eat":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "walk"
            return
        if self.state == "climb":
            step = self.speed * 0.8 * dt
            self.anim += dt * 8
            if abs(self.target - self.y) <= step:
                self.y, self.state = self.target, "walk"
                self.dir = _sign(player.x - self.x) or self.rng.choice((-1, 1))
            else:
                self.y += step * _sign(self.target - self.y)
            return

        self.anim += dt * 9
        self.x += self.dir * self.speed * dt
        row = round((self.y - OY) / TILE)
        ahead = self.x + self.dir * 6
        if ahead < 8 or ahead > W - 8 or (row, int(ahead // TILE)) not in level.floors:
            self.dir = -self.dir
            self.x += self.dir * self.speed * dt * 2
        col = int(self.x // TILE)
        cx = col * TILE + TILE / 2

        cell = (row - 1, col)
        if cell in level.grain and abs(self.x - cx) < 6:
            level.grain.discard(cell)
            self.state, self.timer = "eat", 0.9
            return

        if abs(self.x - cx) > 8:
            self.last_col = None
        if abs(self.x - cx) <= self.speed * dt + 0.8 and self.last_col != col:
            self.last_col = col
            below, above = player.y > self.y + 10, player.y < self.y - 10
            options = []
            if (row, col) in level.ladders:
                options.append(("down", below))
            if (row - 1, col) in level.ladders:
                options.append(("up", above))
            for way, wanted in options:
                if self.rng.random() < (0.85 if wanted else 0.12):
                    top, bot = level.ladder_span(col, row if way == "down" else row - 1)
                    self.x, self.state = cx, "climb"
                    self.target = bot if way == "down" else top
                    return

    def frame(self):
        if self.state == "eat":
            return "eat"
        if self.state == "climb":
            return "w%d" % (int(self.anim) % 2)
        return "w%d" % (int(self.anim) % 2)


class Bird:
    """The big bird: caged on levels 1-8, loose and hunting Harry from level 9."""

    def __init__(self, level_no, rng):
        self.n = level_no
        self.rng = rng
        self.reset()

    def reset(self):
        self.x, self.y = CAGE_CENTER
        self.vx = self.vy = 0.0
        self.delay = 2.6
        self.mode, self.mtimer = "chase", 5.5
        self.goal = (self.x, self.y)
        self.t = 0.0

    def update(self, dt, player):
        self.t += dt
        if self.delay > 0:
            self.delay -= dt
            self.y = CAGE_CENTER[1] + math.sin(self.t * 12) * 1.5
            return
        speed = bird_speed(self.n)
        self.mtimer -= dt
        if self.mode == "chase":
            tx, ty = player.x, player.y - 10 + math.sin(self.t * 3) * 14
            if self.mtimer <= 0:
                self.mode, self.mtimer = "retreat", 1.8
                self.goal = (self.rng.choice((30, W - 30)), self.rng.choice((50, 110, 170)))
        else:
            tx, ty = self.goal
            if self.mtimer <= 0:
                self.mode, self.mtimer = "chase", 5.5
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy) or 1.0
        k = min(1.0, dt * 1.6)
        self.vx += (dx / d * speed - self.vx) * k
        self.vy += (dy / d * speed - self.vy) * k
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def free(self):
        return self.delay <= 0

    def hits(self, player):
        if not self.free:
            return False
        px, py = player.center()
        return math.hypot(px - self.x, py - self.y) < 12
