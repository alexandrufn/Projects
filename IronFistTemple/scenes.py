"""Game screens: title, controls, floor intro, the floor itself, results, game over and the ending."""
import math
import random

import pygame
from pygame.locals import (KEYDOWN, JOYBUTTONDOWN, JOYHATMOTION, K_UP, K_DOWN, K_LEFT, K_RIGHT, K_w, K_a, K_s, K_d,
                           K_SPACE, K_z, K_x, K_j, K_k, K_ESCAPE, K_p, K_RETURN, K_KP_ENTER, K_BACKSPACE, KMOD_ALT)

import gfx
from bosses import Boss
from config import (W, H, GROUND, HUD_H, FLOORS, BOSSES, CHARS, ATTACKS, DIFFICULTIES, DIFF_TUNING, START_LIVES,
                    PLAYER_HP, EXTRA_LIFE_EVERY)
from fighters import Player, Enemy, Input, Pot, Flame, clamp, wrect

GOLD = (238, 190, 84)
CREAM = (255, 238, 208)
RED = (236, 76, 60)
DIM = (176, 142, 120)

JUMP_KEYS = (K_UP, K_w, K_SPACE)
PUNCH_KEYS = (K_z, K_j)
KICK_KEYS = (K_x, K_k)
LEFT_KEYS = (K_LEFT, K_a)
RIGHT_KEYS = (K_RIGHT, K_d)
DOWN_KEYS = (K_DOWN, K_s)


def menu_action(e):
    if e.type == KEYDOWN:
        if e.mod & KMOD_ALT:
            return None
        if e.key in (K_UP, K_w):
            return "up"
        if e.key in (K_DOWN, K_s):
            return "down"
        if e.key in (K_LEFT, K_a):
            return "left"
        if e.key in (K_RIGHT, K_d):
            return "right"
        if e.key in (K_RETURN, K_KP_ENTER, K_SPACE, K_z, K_j, K_x, K_k):
            return "ok"
        if e.key in (K_ESCAPE, K_BACKSPACE):
            return "back"
    elif e.type == JOYHATMOTION:
        hx, hy = e.value
        return "up" if hy == 1 else "down" if hy == -1 else "left" if hx == -1 else "right" if hx == 1 else None
    elif e.type == JOYBUTTONDOWN:
        return "ok" if e.button in (0, 2, 7) else "back" if e.button == 1 else None
    return None


def overlay(surf, alpha=150, color=(8, 4, 8)):
    o = pygame.Surface((W, H), pygame.SRCALPHA)
    o.fill((*color, alpha))
    surf.blit(o, (0, 0))


def draw_menu(surf, items, sel, cx, y, t, gap=15, size=14):
    for i, s in enumerate(items):
        yy = y + i * gap
        if i == sel:
            w = gfx.text_width(s, size)
            bob = int(math.sin(t * 8) * 1.5)
            gfx.text(surf, s, size, (cx, yy), GOLD, outline=True)
            gfx.text(surf, ">", size, (cx - w // 2 - 9 + bob, yy), GOLD, outline=True)
            gfx.text(surf, "<", size, (cx + w // 2 + 9 - bob, yy), GOLD, outline=True)
        else:
            gfx.text(surf, s, size, (cx, yy), DIM)


class Scene:
    def __init__(self, app):
        self.app = app

    def handle(self, events):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


# =============================================================================
# Title
# =============================================================================
class TitleScene(Scene):
    def __init__(self, app, sel=0):
        super().__init__(app)
        self.bg = gfx.Background("ember", seed=3)
        self.sel = sel
        self.t = 0.0
        self.cam = 0.0
        self.pose = ("idle", 0.0)
        self.pose_t = 0.0
        self.title = gfx.fancy_text("IRON FIST", 54, (255, 244, 170), (230, 90, 30), thick=2)
        self.sub = gfx.fancy_text("TEMPLE OF THE DRAGON", 20, (255, 255, 255), (190, 196, 230), thick=1)
        self.floor_sel = 0
        self.items = []
        self._items()
        app.audio.music("temple")

    def _items(self):
        s = self.app.save
        reach = min(4, s.get("reached", 0))
        self.floor_sel = min(self.floor_sel, reach)
        self.items = ["NEW GAME",
                      "FLOOR  < %d >" % (self.floor_sel + 1) if reach > 0 else "FLOOR  1",
                      "DIFFICULTY  < %s >" % DIFFICULTIES[s.get("diff", 1)],
                      "CONTROLS", "QUIT"]

    def handle(self, events):
        s = self.app.save
        for e in events:
            a = menu_action(e)
            if a in ("up", "down"):
                self.sel = (self.sel + (1 if a == "down" else -1)) % len(self.items)
                self.app.audio.play("blip")
            elif a in ("left", "right"):
                d = 1 if a == "right" else -1
                if self.sel == 2:
                    s["diff"] = (s.get("diff", 1) + d) % 3
                    self.app.audio.play("blip")
                    self.app.write_save()
                elif self.sel == 1:
                    reach = min(4, s.get("reached", 0))
                    self.floor_sel = clamp(self.floor_sel + d, 0, reach)
                    self.app.audio.play("blip")
                self._items()
            elif a == "ok":
                self.app.audio.play("select")
                if self.sel in (0, 1):
                    fl = 0 if self.sel == 0 else self.floor_sel
                    self.app.change(IntroScene(self.app, fl, START_LIVES, 0))
                elif self.sel == 2:
                    s["diff"] = (s.get("diff", 1) + 1) % 3
                    self.app.write_save()
                    self._items()
                elif self.sel == 3:
                    self.app.change(ControlsScene(self.app))
                else:
                    self.app.quit()
            elif a == "back":
                self.app.quit()

    def update(self, dt):
        self.t += dt
        self.cam += 18 * dt
        self.bg.update(dt)
        self.pose_t += dt
        if self.pose_t > 1.6:
            self.pose_t = 0.0
            self.pose = random.choice((("punch", 0), ("kick", 0), ("jkick", 0), ("idle", 0)))
        elif self.pose_t > 0.5:
            self.pose = ("idle", self.t * 0.6)

    def draw(self, surf):
        self.bg.draw(surf, self.cam)
        self.bg.draw_motes(surf)
        hero = CHARS["hero"]
        img, (ax, ay) = gfx.frame("hero", hero, self.pose[0], self.pose[1] % 1, False)
        big = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
        surf.blit(big, (62 - ax * 2, GROUND + 6 - ay * 2 - (14 if self.pose[0] == "jkick" else 0)))
        zh = CHARS["zhao"]
        img, (ax, ay) = gfx.frame("zhao", zh, "idle" if self.pose_t < 1.1 else "burst_w", (self.t * 0.5) % 1, True)
        big = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
        surf.blit(big, (W - 62 - ax * 2, GROUND + 6 - ay * 2))
        overlay(surf, 60)
        surf.blit(self.title, self.title.get_rect(center=(W // 2, 52 + int(math.sin(self.t * 1.6) * 2))))
        surf.blit(self.sub, self.sub.get_rect(center=(W // 2, 82)))
        p = pygame.Rect(0, 0, 190, 90)
        p.center = (W // 2, 142)
        gfx.panel(surf, p)
        draw_menu(surf, self.items, self.sel, W // 2, p.y + 14, self.t, gap=16, size=13)
        gfx.text(surf, "HI-SCORE  %06d" % self.app.save.get("hi", 0), 12, (W // 2, 200), CREAM, outline=True)
        gfx.text(surf, "F11 FULLSCREEN", 10, (W - 4, H - 6), DIM, anchor="bottomright")


# =============================================================================
# Controls
# =============================================================================
class ControlsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = gfx.Background("moon", seed=9)
        self.t = 0.0

    def handle(self, events):
        for e in events:
            if menu_action(e) in ("ok", "back"):
                self.app.audio.play("blip")
                self.app.change(TitleScene(self.app, sel=3))

    def update(self, dt):
        self.t += dt
        self.bg.update(dt)

    def draw(self, surf):
        self.bg.draw(surf, 0)
        overlay(surf, 130)
        p = pygame.Rect(18, 14, W - 36, H - 28)
        gfx.panel(surf, p)
        surf.blit(t := gfx.fancy_text("CONTROLS", 26, (255, 244, 170), (230, 90, 30)), t.get_rect(center=(W // 2, 32)))
        rows = [("MOVE", "LEFT / RIGHT  OR  A / D"), ("JUMP", "UP  OR  W  OR  SPACE"), ("CROUCH", "DOWN  OR  S"),
                ("PUNCH", "Z  OR  J"), ("KICK", "X  OR  K"), ("PAUSE", "ESC  OR  P"), ("GAMEPAD", "STICK + A JUMP, X PUNCH, B KICK")]
        y = 54
        for a, b in rows:
            gfx.text(surf, a, 12, (40, y), DIM, anchor="midleft")
            gfx.text(surf, b, 12, (130, y), CREAM, anchor="midleft")
            y += 13
        tips = ("CROUCH TO DUCK HIGH KNIVES, JUMP OVER LOW ONES. CROUCH + PUNCH OR KICK HITS LOW ENEMIES. "
                "PRESS KICK OR PUNCH IN THE AIR FOR A FLYING KICK. WHEN GRABBED, TAP LEFT AND RIGHT TO SHAKE FREE. "
                "BOSSES TELEGRAPH THEIR ATTACKS. WATCH THEIR POSE, THEN PUNISH THEIR RECOVERY.")
        y += 6
        for line in gfx.wrap(tips, 12, p.w - 24):
            gfx.text(surf, line, 12, (W // 2, y), CREAM)
            y += 11
        if int(self.t * 2) % 2 == 0:
            gfx.text(surf, "PRESS FIRE TO RETURN", 12, (W // 2, H - 26), GOLD, outline=True)


# =============================================================================
# Floor intro card
# =============================================================================
class IntroScene(Scene):
    def __init__(self, app, floor, lives, score):
        super().__init__(app)
        self.floor, self.lives, self.score = floor, lives, score
        self.cfg = FLOORS[floor]
        self.boss = BOSSES[self.cfg["boss"]]
        self.bg = gfx.Background(self.cfg["bg"], seed=floor + 3)
        self.t = 0.0
        self.cam = 0.0
        app.audio.music(None)
        app.audio.play("gong")

    def handle(self, events):
        for e in events:
            a = menu_action(e)
            if a == "ok" and self.t > 0.6:
                self.app.audio.play("select")
                self.app.change(GameScene(self.app, self.floor, self.lives, self.score))
            elif a == "back":
                self.app.change(TitleScene(self.app))

    def update(self, dt):
        self.t += dt
        self.cam += 10 * dt
        self.bg.update(dt)

    def draw(self, surf):
        self.bg.draw(surf, self.cam)
        overlay(surf, 150)
        gfx.text(surf, "FLOOR %d" % (self.floor + 1), 16, (W // 2, 26), DIM, outline=True)
        nm = gfx.fancy_text(self.cfg["name"], 24, (255, 244, 170), (230, 90, 30))
        surf.blit(nm, nm.get_rect(center=(W // 2, 50)))
        # guardian portrait
        b = self.boss
        char = CHARS[b["key"]]
        slide = max(0, int((0.5 - self.t) * 600))
        img, (ax, ay) = gfx.frame(b["key"], char, "staff_idle" if b["key"] == "hu" else "idle",
                                  (self.t * 0.6) % 1, True)
        sc = 2
        big = pygame.transform.scale(img, (img.get_width() * sc, img.get_height() * sc))
        panel = pygame.Rect(26 - slide, 72, 124, 122)
        gfx.panel(surf, panel)
        surf.blit(big, (panel.centerx - ax * sc + 4, panel.bottom - 8 - ay * sc))
        x = 168 + slide
        gfx.text(surf, "GUARDIAN", 12, (x, 80), RED, anchor="midleft", outline=True)
        gfx.text(surf, b["name"], 14, (x, 96), GOLD, anchor="midleft", outline=True)
        gfx.text(surf, b["title"], 12, (x, 110), CREAM, anchor="midleft", outline=True)
        q = pygame.Rect(x - 4, 124, W - x - 14, 44)
        gfx.panel(surf, q)
        for k, line in enumerate(gfx.wrap('"%s"' % b["quote"], 12, q.w - 12)[:4]):
            gfx.text(surf, line, 12, (q.x + 6, q.y + 8 + k * 10), CREAM, anchor="midleft")
        gfx.text(surf, "%d HITS TO DEFEAT" % b["hp"], 12, (x, 180), DIM, anchor="midleft", outline=True)
        gfx.text(surf, "LIVES %d    SCORE %06d" % (self.lives, self.score), 12, (W // 2, 205), CREAM, outline=True)
        if int(self.t * 2.5) % 2 == 0 and self.t > 0.6:
            gfx.text(surf, "PRESS FIRE TO FIGHT", 14, (x + 52, 193), GOLD, outline=True)


# =============================================================================
# Particles
# =============================================================================
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "size", "grav", "kind", "drag")

    def __init__(self, x, y, vx, vy, life, color, size=1, grav=0.0, kind="px", drag=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color, self.size, self.grav, self.kind, self.drag = color, size, grav, kind, drag

    def update(self, dt):
        self.vy += self.grav * dt
        if self.drag:
            k = max(0.0, 1 - self.drag * dt)
            self.vx *= k
            self.vy *= k
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf, cam):
        x, y = int(self.x - cam), int(self.y)
        t = self.life / self.max
        k = self.kind
        if k == "px":
            surf.fill(self.color, (x, y, self.size, self.size))
        elif k == "smoke":
            r = int(self.size + (1 - t) * 4)
            a = int(130 * t) // 16 * 16
            if a > 0:
                c = gfx.soft_circle(r, self.color, a)
                surf.blit(c, (x - r, y - r))
        elif k == "ring":
            r = int(self.size * (1 - t) + 2)
            pygame.draw.circle(surf, gfx.lerp((0, 0, 0), self.color, min(1.0, t * 1.4)), (x, y), r, 2 if t > 0.4 else 1)
        elif k == "star":
            r = max(2, int(self.size * (0.4 + t * 0.6)))
            img = gfx.impact_star(r)
            surf.blit(img, (x - r, y - r))
        elif k == "flame":
            r = max(1, int(self.size * t) + 1)
            surf.blit(gfx.glow(r * 3, self.color), (x - r * 3, y - r * 3), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(surf, gfx.lerp((255, 240, 180), self.color, 1 - t), (x, y), r)


class FloatText:
    def __init__(self, x, y, s, color=GOLD, life=1.0, size=12):
        self.x, self.y, self.s, self.color, self.life, self.size = x, y, s, color, life, size

    def update(self, dt):
        self.y -= 16 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf, cam):
        if self.life > 0.2 or int(self.life * 30) % 2:
            gfx.text(surf, self.s, self.size, (int(self.x - cam), int(self.y)), self.color, outline=True)


# =============================================================================
# The floor
# =============================================================================
class GameScene(Scene):
    def __init__(self, app, floor, lives, score, restart_boss_hp=None):
        super().__init__(app)
        self.audio = app.audio
        self.tune = DIFF_TUNING[app.save.get("diff", 1)]
        self.floor = floor
        self.cfg = FLOORS[floor]
        self.lives = lives
        self.score = score
        self.next_life = (score // EXTRA_LIFE_EVERY + 1) * EXTRA_LIFE_EVERY
        self.bg = gfx.Background(self.cfg["bg"], seed=floor + 3)
        self.world = pygame.Surface((W, H)).convert()
        self.hud = gfx.hud_bar()
        self.player = Player()
        self.length = self.cfg["length"]
        self.cam_max = self.length - W
        self.cam = 0.0
        self.time = float(self.cfg["time"])
        self.enemies, self.projs, self.hazards, self.particles, self.texts = [], [], [], [], []
        self.boss = None
        self.state = "ready"
        self.state_t = 0.0
        self.shake = 0.0
        self.hitstop = 0.0
        self.slow = 0.0
        self.flash_player = 0.0
        self.screen_flash = 0.0
        self.paused = False
        self.pause_sel = 0
        self.buf = {"jump": 0.0, "punch": 0.0, "kick": 0.0}
        self.dirpress = 0
        self.banner = None
        self.checkpoint = 40.0
        self.cp_taken = False
        self.dead_timer = 0.0
        self.boss_hp_keep = None
        self.t = 0.0
        self.zone_cleared = 0
        rng = random.Random(floor * 131 + 7)
        self._build_script(rng)
        self._build_hazards(rng)
        self.player.reset(40)
        self.banner = ("FLOOR %d" % (floor + 1), 1.8, self.cfg["name"])
        app.audio.music("temple")

    # ------------------------------------------------------------- level build
    def _build_script(self, rng):
        cfg = self.cfg
        kinds, weights = zip(*cfg["pool"])
        self.spawns = []
        x = 220.0
        end = self.cam_max - 40
        while x < end:
            kind = rng.choices(kinds, weights)[0]
            side = -1 if (kind == "grab" and rng.random() < 0.4) or (kind in ("imp",) and rng.random() < 0.35) else 1
            self.spawns.append([x, kind, side])
            if kind == "grab" and rng.random() < 0.3:
                self.spawns.append([x + 8, "grab", -side])
            x += rng.uniform(*cfg["gap"])

    def _build_hazards(self, rng):
        lo, hi = 380.0, self.cam_max - 110
        for kind, n in self.cfg["hazards"]:
            for i in range(n):
                x = lo + (hi - lo) * (i + rng.uniform(0.1, 0.9)) / n
                self.hazards.append(Pot(x) if kind == "pot" else Flame(x, rng.uniform(0, 3.4)))

    # ------------------------------------------------------------- services for other modules
    def player_bounds(self):
        return max(10.0, self.cam + 10), self.cam + W - 10

    def screen_bounds(self, x):
        return self.cam + 18, self.cam + W - 18

    def minion_count(self):
        return sum(1 for e in self.enemies if e.alive and not e.dying)

    def spawn_enemy(self, kind, x):
        face = 1 if x < self.player.x else -1
        e = Enemy(kind, x, self, face)
        self.enemies.append(e)
        return e

    def dust(self, x, y, n=3):
        c = gfx.shade(self.bg.t["floor"][0], 1.2)
        for _ in range(n):
            self.particles.append(Particle(x + random.uniform(-4, 4), y - 1, random.uniform(-14, 14), random.uniform(-14, -3),
                                           random.uniform(0.3, 0.6), c, size=2, kind="smoke", drag=1.5))

    def spark(self, x, y):
        self.particles.append(Particle(x, y, 0, 0, 0.14, (255, 255, 220), size=7, kind="star"))
        for _ in range(7):
            a = random.uniform(0, math.tau)
            sp = random.uniform(40, 120)
            self.particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.uniform(0.15, 0.35),
                                           random.choice(((255, 240, 160), (255, 190, 90), (255, 255, 255))),
                                           grav=260))

    def ring(self, x, y, color, big=False):
        self.particles.append(Particle(x, y, 0, 0, 0.45, color, size=44 if big else 22, kind="ring"))

    def debris(self, x, y, color, n=10):
        for _ in range(n):
            self.particles.append(Particle(x, y, random.uniform(-70, 70), random.uniform(-100, -20),
                                           random.uniform(0.5, 1.0), random.choice((color, gfx.shade(color, 0.7),
                                                                                    gfx.shade(color, 1.3))),
                                           size=random.choice((1, 2, 2)), grav=420))

    def flame_breath(self, x, y, facing):
        for _ in range(3):
            self.particles.append(Particle(x, y + random.uniform(-3, 3), facing * random.uniform(80, 170),
                                           random.uniform(-14, 14), random.uniform(0.25, 0.5),
                                           random.choice(((255, 120, 40), (255, 190, 70), (230, 70, 30))),
                                           size=random.randint(3, 6), kind="flame"))

    def flash_screen(self, t):
        self.screen_flash = t

    def on_player_hit(self, dmg):
        self.shake = max(self.shake, 4)
        self.hitstop = max(self.hitstop, 0.07)
        self.flash_player = 0.12
        self.audio.play("hurt")
        self.spark(self.player.x, GROUND - 28)

    def on_boss_dead(self, boss):
        self.state = "boss_dead"
        self.state_t = 0.0
        self.slow = 1.4
        self.hitstop = 0.18
        self.shake = 10
        self.audio.play("boom")
        self.audio.music(None)
        self.score_add(BOSSES[boss.idx]["bonus"], boss.x, GROUND - 70, big=True)
        self.projs.clear()
        for e in self.enemies:
            if not e.dying:
                e.hit(99, self, self.player)
        self.screen_flash = 0.25

    def score_add(self, pts, x, y, big=False):
        self.score += pts
        self.texts.append(FloatText(x, y, str(pts), GOLD, 1.0, 14 if big else 11))
        while self.score >= self.next_life:
            self.lives += 1
            self.next_life += EXTRA_LIFE_EVERY
            self.texts.append(FloatText(self.player.x, GROUND - 70, "EXTRA LIFE!", (130, 255, 150), 1.5, 14))
            self.audio.play("win")

    # ------------------------------------------------------------------ input
    def handle(self, events):
        for e in events:
            if self.paused:
                a = menu_action(e)
                if a in ("up", "down"):
                    self.pause_sel ^= 1
                    self.audio.play("blip")
                elif a == "ok":
                    if self.pause_sel == 0:
                        self.paused = False
                    else:
                        self.app.change(TitleScene(self.app))
                elif a == "back":
                    self.paused = False
                continue
            if (e.type == KEYDOWN and e.key in (K_ESCAPE, K_p)) or (e.type == JOYBUTTONDOWN and e.button == 7):
                self.paused = True
                self.pause_sel = 0
                self.audio.play("blip")
                continue
            if e.type == KEYDOWN:
                if e.key in JUMP_KEYS:
                    self.buf["jump"] = 0.12
                elif e.key in PUNCH_KEYS:
                    self.buf["punch"] = 0.12
                elif e.key in KICK_KEYS:
                    self.buf["kick"] = 0.12
                if e.key in LEFT_KEYS:
                    self.dirpress = -1
                elif e.key in RIGHT_KEYS:
                    self.dirpress = 1
            elif e.type == JOYBUTTONDOWN:
                if e.button == 0:
                    self.buf["jump"] = 0.12
                elif e.button == 2:
                    self.buf["punch"] = 0.12
                elif e.button in (1, 3):
                    self.buf["kick"] = 0.12
            elif e.type == JOYHATMOTION:
                if e.value[0]:
                    self.dirpress = e.value[0]
                if e.value[1] == 1:
                    self.buf["jump"] = 0.12

    def _read_input(self):
        k = pygame.key.get_pressed()
        i = Input()
        mx = (any(k[c] for c in RIGHT_KEYS)) - (any(k[c] for c in LEFT_KEYS))
        down = any(k[c] for c in DOWN_KEYS)
        for j in self.app.joysticks:
            try:
                ax, ay = j.get_axis(0), j.get_axis(1)
                if abs(ax) > 0.4:
                    mx += 1 if ax > 0 else -1
                if ay > 0.5:
                    down = True
                if ay < -0.6:
                    self.buf["jump"] = max(self.buf["jump"], 0.05)
                if j.get_numhats():
                    hx, hy = j.get_hat(0)
                    mx += hx
                    down = down or hy == -1
            except pygame.error:
                pass
        i.mx = int(clamp(mx, -1, 1))
        i.down = down
        i.jump = self.buf["jump"] > 0
        i.punch = self.buf["punch"] > 0
        i.kick = self.buf["kick"] > 0
        i.dir = self.dirpress
        self.dirpress = 0
        return i

    # ----------------------------------------------------------------- update
    def update(self, dt):
        if self.paused:
            return
        self.t += dt
        for k in self.buf:
            self.buf[k] = max(0.0, self.buf[k] - dt)
        self.bg.update(dt)
        self.particles = [p for p in self.particles if p.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]
        self.shake = max(0.0, self.shake - dt * 22)
        self.screen_flash = max(0.0, self.screen_flash - dt)
        self.flash_player = max(0.0, self.flash_player - dt)
        if self.hitstop > 0:
            self.hitstop -= dt
            return
        if self.slow > 0:
            self.slow -= dt
            dt *= 0.35
        self.state_t += dt
        if self.banner:
            s, t, sub = self.banner
            self.banner = (s, t - dt, sub) if t - dt > 0 else None
        st = self.state
        p = self.player

        if st == "ready":
            if self.state_t > 1.8:
                self.state = "play"
                self.state_t = 0.0
            return

        inp = self._read_input() if not p.dead and st not in ("boss_dead", "clear") else Input()
        p.update(dt, inp, self)
        for u in p.used:
            self.buf[u] = 0.0

        if st in ("play", "boss_intro", "boss"):
            self.time -= dt
            if self.time <= 0 and not p.dead:
                self.time = 0
                self.banner = ("TIME UP!", 1.4, "")
                p.die(p.x + 1, self)
            elif self.time < 20 and int(self.time) != int(self.time + dt):
                self.audio.play("tick", 0.5)

        self._camera(dt)

        if st == "play":
            self._spawn()
            if (not self.cp_taken and p.x > self.length * 0.5 and not p.dead):
                self.cp_taken = True
                self.checkpoint = p.x
                self.texts.append(FloatText(p.x, GROUND - 70, "CHECKPOINT", (150, 255, 170), 1.4))
                self.audio.play("select", 0.6)
            if self.cam >= self.cam_max - 0.5 and not p.dead:
                self._start_boss()
        for h in self.hazards:
            h.update(dt, self)
        self.hazards = [h for h in self.hazards if h.alive]
        for e in self.enemies:
            e.update(dt, self)
        self.enemies = [e for e in self.enemies if e.alive and self.cam - 160 < e.x < self.cam + W + 160]
        for pr in self.projs:
            pr.update(dt, self)
        self.projs = [pr for pr in self.projs if pr.alive]
        if self.boss:
            self.boss.update(dt, self)
            if st == "boss_intro" and self.boss.state == "fight":
                self.state = "boss"
                self.state_t = 0.0
                self.audio.music("boss")

        if not p.dead:
            self._player_attacks()
            self._hurt_player(dt)
        self._after_death(dt)

        if st == "boss_dead":
            if int(self.state_t * 12) % 3 == 0 and self.boss:
                self.spark(self.boss.x + random.uniform(-20, 20), GROUND - random.uniform(10, 70))
            if self.state_t > 1.7 and self.state_t < 1.8:
                p.victory = True
            if self.state_t > 3.2:
                self._floor_clear()

    def _camera(self, dt):
        p = self.player
        if self.state in ("boss_intro", "boss", "boss_dead", "clear"):
            self.cam = self.cam_max
            return
        target = clamp(p.x - 150, 0, self.cam_max)
        if target > self.cam:
            self.cam += (target - self.cam) * min(1.0, 6 * dt)
            self.cam = min(self.cam, self.cam_max)

    def _spawn(self):
        p = self.player
        while self.spawns and p.x >= self.spawns[0][0]:
            x, kind, side = self.spawns[0]
            if self.minion_count() >= 5:
                break
            self.spawns.pop(0)
            if kind in ("knife", "snake") and p.x < self.cam + 100 and side == -1:
                side = 1
            ex = self.cam - 16 if side < 0 else self.cam + W + 16
            if self.cam <= 0 and side < 0:
                ex = self.cam + W + 16
            self.spawn_enemy(kind, ex)

    def _start_boss(self):
        self.state = "boss_intro"
        self.state_t = 0.0
        self.boss = Boss(self.cfg["boss"], self)
        for e in self.enemies:
            if not e.dying:
                e.dying = True
                e.dead_t = 0.0
                e.vz = 100
                e.vx = random.uniform(-60, 60)
        self.projs.clear()
        self.hazards = [h for h in self.hazards if h.x < self.cam + W + 40 and h.x > self.cam - 40]
        self.audio.music(None)
        self.audio.play("gong")
        b = BOSSES[self.cfg["boss"]]
        self.banner = (b["name"], 2.4, b["title"])

    # ---------------------------------------------------------------- combat
    def _player_attacks(self):
        p = self.player
        r = p.attack_rect()
        if not r:
            return
        a = ATTACKS[p.atk]
        heavy = p.atk in ("kick", "ckick", "jkick")
        for e in self.enemies:
            if e.dying or id(e) in p.hit_ids:
                continue
            if r.colliderect(e.hurtbox()):
                p.hit_ids.add(id(e))
                res = e.hit(a["dmg"], self, p)
                cx, cy = r.centerx, r.centery
                if res == "blocked":
                    continue
                self.audio.play("kick" if heavy else "punch")
                self.spark(cx, cy)
                self.hitstop = max(self.hitstop, 0.05)
                if res == "killed":
                    self.audio.play("die", 0.6)
                    self.shake = max(self.shake, 3)
                    self.score_add(e.pts + (100 if p.atk == "jkick" else 0), e.x, GROUND - 56)
                else:
                    self.shake = max(self.shake, 2)
        b = self.boss
        if b and b.state == "fight" and id(b) not in p.hit_ids and r.colliderect(b.hurtbox()):
            res = b.hit(a["dmg"], self, p)
            if res:
                p.hit_ids.add(id(b))
                if res in ("hit", "killed"):
                    self.audio.play("kick" if heavy else "punch")
                    self.spark(r.centerx, r.centery)
                    self.hitstop = max(self.hitstop, 0.07 if heavy else 0.05)
                    self.shake = max(self.shake, 3 if heavy else 2)
                    self.score_add(a["pts"], b.x, GROUND - 60 * b.s)
        for pr in self.projs:
            if pr.destroyable and pr.alive and r.colliderect(pr.rect()):
                pr.alive = False
                self.spark(pr.x, pr.y)
                self.audio.play("spark")
                self.score_add(50, pr.x, pr.y - 10, big=False)

    def _hurt_player(self, dt):
        p = self.player
        pr = p.hurtbox()
        for e in self.enemies:
            if e.dying:
                continue
            e.hcd = max(0.0, getattr(e, "hcd", 0.0) - dt)
            r = e.attack_rect()
            if r and r.colliderect(pr) and e.hcd <= 0:
                if p.take_hit(e.atk["dmg"], e.x, self, kb=0.8):
                    e.hcd = e.atk.get("tick", 0.0) or 0.0
                    if not e.atk.get("tick"):
                        e.atk = None
        for proj in self.projs:
            if proj.alive and proj.rect().colliderect(pr) and not proj.hit:
                if p.take_hit(proj.dmg, proj.x, self, kb=0.9):
                    proj.hit = True
                    if proj.kind in ("knife", "fire"):
                        proj.alive = False
        b = self.boss
        if b and b.atk and b.state == "fight":
            r = b.attack_rect()
            a = b.atk
            a["cd"] = max(0.0, a.get("cd", 0.0) - dt)
            if r and r.colliderect(pr) and a["cd"] <= 0:
                if a["tick"] > 0 or not a["hit"]:
                    if p.take_hit(a["dmg"], b.x, self, kb=a["kb"], stun=0.34):
                        a["hit"] = True
                        a["cd"] = a["tick"]

    # ------------------------------------------------------------ death / clear
    def _after_death(self, dt):
        p = self.player
        if not p.dead:
            return
        self.dead_timer += dt
        if self.dead_timer > 2.0:
            self.dead_timer = 0.0
            self.lives -= 1
            if self.lives < 0:
                self.app.update_hi(self.score, self.floor)
                self.app.change(GameOverScene(self.app, self.floor, self.score))
                return
            self._respawn()

    def _respawn(self):
        p = self.player
        in_boss = self.boss is not None
        x = self.cam + 60 if in_boss else self.checkpoint
        p.reset(x)
        self.time = max(self.time, 90.0)
        self.enemies.clear()
        self.projs.clear()
        if in_boss:
            self.state = "boss" if self.boss.state != "intro" else "boss_intro"
            self.boss.atk = None
            self.boss.gen = None
            self.boss.armor = False
            self.boss.stun = 0
            self.boss.x = self.cam + W - 80
            self.boss.state = "fight"
            self.boss.neutral = 1.2
            self.state = "boss"
            self.boss.alpha = 255
        else:
            self.cam = clamp(self.checkpoint - 150, 0, self.cam_max)
            self.spawns = [s for s in self.spawns if s[0] > self.checkpoint + 80]
            self.hazards = [h for h in self.hazards if h.x > self.checkpoint + 100 or h.kind == "flame"]
        p.invuln = 1.5
        self.banner = ("GET UP, FIGHT!", 1.2, "")

    def _floor_clear(self):
        self.state = "clear"
        self.app.update_hi(self.score, self.floor)
        self.app.change(ClearScene(self.app, self.floor, self.lives, self.score, self.time, self.player.hp))

    # ------------------------------------------------------------------- draw
    def draw(self, surf):
        w = self.world
        w.fill((10, 6, 10))
        cam = self.cam
        self.bg.draw(w, cam)
        # hazards first (floor level), then everyone sorted (no depth lane: draw order is simple)
        for h in self.hazards:
            h.draw(w, cam)
        for e in self.enemies:
            e.draw(w, cam)
        if self.boss:
            self.boss.draw(w, cam)
        self.player.draw(w, cam, self.flash_player > 0)
        for pr in self.projs:
            pr.draw(w, cam)
        for pt in self.particles:
            pt.draw(w, cam)
        self.bg.draw_motes(w)
        for t in self.texts:
            t.draw(w, cam)
        if self.bg.t["mood"]:
            tint = self.bg.t["mood"]
            w.fill(tint, special_flags=pygame.BLEND_RGB_MULT) if False else None
        # vignette-ish darkening on the sides
        sh = self.shake
        ox = int(random.uniform(-sh, sh)) if sh > 0.5 else 0
        oy = int(random.uniform(-sh, sh)) if sh > 0.5 else 0
        surf.fill((8, 4, 8))
        surf.blit(w, (ox, oy))
        self._draw_hud(surf)
        self._draw_banner(surf)
        if self.screen_flash > 0:
            overlay(surf, int(200 * min(1.0, self.screen_flash / 0.25)), (255, 250, 235))
        if self.paused:
            overlay(surf, 160)
            p = pygame.Rect(0, 0, 150, 66)
            p.center = (W // 2, H // 2)
            gfx.panel(surf, p)
            gfx.text(surf, "PAUSED", 16, (W // 2, p.y + 14), CREAM, outline=True)
            draw_menu(surf, ["RESUME", "QUIT TO TITLE"], self.pause_sel, W // 2, p.y + 36, self.t, gap=14, size=13)

    def _draw_hud(self, surf):
        surf.blit(self.hud, (0, 0))
        p = self.player
        gfx.text(surf, "SCORE %06d" % self.score, 12, (6, 6), CREAM, anchor="midleft")
        gfx.text(surf, "FLOOR %d" % (self.floor + 1), 12, (140, 6), GOLD, anchor="midleft")
        tcol = RED if self.time < 20 and int(self.time * 3) % 2 else CREAM
        gfx.text(surf, "TIME %03d" % int(self.time), 12, (215, 6), tcol, anchor="midleft")
        gfx.text(surf, "HI %06d" % self.app.save.get("hi", 0), 12, (W - 6, 6), DIM, anchor="midright")
        gfx.energy_bar(surf, 6, 15, 150, 8, p.hp / PLAYER_HP, (226, 60, 56))
        gfx.text(surf, "KAI", 10, (6, 28), CREAM, anchor="midleft")
        for i in range(max(0, self.lives)):
            gfx.draw_head_icon(surf, 42 + i * 13, 28)
        b = self.boss
        if b:
            frac = max(0.0, b.hp / b.max_hp)
            bx, bw = W - 6 - 170, 170
            gfx.energy_bar(surf, bx, 15, bw, 8, frac, (240, 170, 50) if frac > 0.33 else (255, 90, 50), segs=20)
            gfx.text(surf, BOSSES[b.idx]["name"], 10, (W - 6, 28), GOLD, anchor="midright")
            for k in (0.66, 0.33):
                surf.fill((255, 255, 255), (bx + int(bw * k), 13, 1, 12))

    def _draw_banner(self, surf):
        if not self.banner:
            return
        s, t, sub = self.banner
        a = min(1.0, t / 0.3)
        img = gfx.fancy_text(s, 36 if len(s) < 14 else 24, (255, 244, 170), (230, 90, 30))
        surf.blit(img, img.get_rect(center=(W // 2, 92)))
        if sub:
            gfx.text(surf, sub, 14, (W // 2, 116), CREAM, outline=True)


# =============================================================================
# Floor clear
# =============================================================================
class ClearScene(Scene):
    def __init__(self, app, floor, lives, score, time_left, hp):
        super().__init__(app)
        self.floor, self.lives, self.score0 = floor, lives, score
        self.time_left, self.hp = int(time_left), hp
        self.tb, self.eb = self.time_left * 30, hp * 40
        self.bg = gfx.Background(FLOORS[floor]["bg"], seed=floor + 3)
        self.t = 0.0
        self.shown = 0
        app.audio.music(None)
        app.audio.play("win")
        app.save["reached"] = max(app.save.get("reached", 0), min(4, floor + 1))
        app.write_save()

    def handle(self, events):
        for e in events:
            if menu_action(e) == "ok" and self.t > 1.5:
                self.app.audio.play("select")
                total = self.score0 + self.tb + self.eb
                self.app.update_hi(total, self.floor)
                if self.floor >= len(FLOORS) - 1:
                    self.app.change(EndingScene(self.app, total))
                else:
                    self.app.change(IntroScene(self.app, self.floor + 1, self.lives, total))

    def update(self, dt):
        self.t += dt
        self.bg.update(dt)

    def draw(self, surf):
        self.bg.draw(surf, 0)
        overlay(surf, 150)
        img = gfx.fancy_text("FLOOR CLEARED!", 30, (255, 244, 170), (230, 90, 30))
        surf.blit(img, img.get_rect(center=(W // 2, 40)))
        gfx.text(surf, BOSSES[FLOORS[self.floor]["boss"]]["name"] + " DEFEATED", 12, (W // 2, 66), CREAM, outline=True)
        p = pygame.Rect(0, 0, 220, 82)
        p.center = (W // 2, 118)
        gfx.panel(surf, p)
        rows = [("TIME BONUS", "%d x 30" % self.time_left, self.tb), ("ENERGY BONUS", "%d x 40" % self.hp, self.eb),
                ("SCORE", "", self.score0 + self.tb + self.eb)]
        for i, (a, b, v) in enumerate(rows):
            if self.t > 0.4 + i * 0.5:
                y = p.y + 16 + i * 22
                gfx.text(surf, a, 12, (p.x + 12, y), CREAM, anchor="midleft")
                gfx.text(surf, b, 10, (p.x + 100, y), DIM, anchor="midleft")
                gfx.text(surf, "%06d" % v, 14, (p.right - 12, y), GOLD, anchor="midright", outline=True)
        if self.t > 1.5 and int(self.t * 2.5) % 2 == 0:
            gfx.text(surf, "PRESS FIRE", 14, (W // 2, 180), GOLD, outline=True)


# =============================================================================
# Game over
# =============================================================================
class GameOverScene(Scene):
    def __init__(self, app, floor, score):
        super().__init__(app)
        self.floor, self.score = floor, score
        self.bg = gfx.Background("inferno", seed=5)
        self.t = 0.0
        self.sel = 0
        app.audio.music(None)
        app.audio.play("lose")

    def handle(self, events):
        for e in events:
            a = menu_action(e)
            if a in ("up", "down") and self.t > 0.6:
                self.sel ^= 1
                self.app.audio.play("blip")
            elif a == "ok" and self.t > 1.0:
                self.app.audio.play("select")
                if self.sel == 0:
                    self.app.change(IntroScene(self.app, self.floor, START_LIVES, 0))
                else:
                    self.app.change(TitleScene(self.app))

    def update(self, dt):
        self.t += dt
        self.bg.update(dt)

    def draw(self, surf):
        self.bg.draw(surf, 0)
        overlay(surf, 170)
        img = gfx.fancy_text("GAME OVER", 40, (255, 200, 170), (200, 40, 40))
        surf.blit(img, img.get_rect(center=(W // 2, 56)))
        gfx.text(surf, "YOU FELL ON FLOOR %d" % (self.floor + 1), 13, (W // 2, 92), CREAM, outline=True)
        gfx.text(surf, "SCORE %06d" % self.score, 13, (W // 2, 108), GOLD, outline=True)
        if self.t > 0.6:
            p = pygame.Rect(0, 0, 190, 54)
            p.center = (W // 2, 150)
            gfx.panel(surf, p)
            draw_menu(surf, ["CONTINUE THIS FLOOR", "TITLE"], self.sel, W // 2, p.y + 16, self.t, gap=20, size=13)


# =============================================================================
# Ending
# =============================================================================
class EndingScene(Scene):
    LINES = ["THE DRAGON LORD IS DEFEATED.", "", "THE TEMPLE FALLS SILENT.", "", "LOTUS IS FREE.",
             "THE SEALED GATES OPEN AT LAST", "AND THE FIRST LIGHT OF DAWN", "FILLS THE HALLS.", "", "",
             "IRON FIST: TEMPLE OF THE DRAGON", "", "THANKS FOR PLAYING!"]

    def __init__(self, app, score):
        super().__init__(app)
        self.score = score
        self.bg = gfx.Background("ember", seed=21)
        self.t = 0.0
        self.hero_x = 40.0
        self.cage_open = False
        self.lotus_x = 300.0
        app.audio.music("temple")
        app.save["cleared"] = True
        app.write_save()

    def handle(self, events):
        for e in events:
            if menu_action(e) in ("ok", "back") and self.t > 3:
                self.app.change(TitleScene(self.app))

    def update(self, dt):
        self.t += dt
        self.bg.update(dt)
        if self.t < 4.0:
            self.hero_x = min(255, self.hero_x + 62 * dt)
        elif not self.cage_open:
            self.cage_open = True
            self.app.audio.play("break")
            self.app.audio.play("win", 0.6)
        elif self.t > 6.0:
            self.lotus_x = max(272, self.lotus_x - 30 * dt)

    def draw(self, surf):
        self.bg.draw(surf, 0)
        hero, lotus = CHARS["hero"], CHARS["lotus"]
        # cage
        cx = 312
        if not self.cage_open:
            for k in range(-14, 15, 7):
                pygame.draw.line(surf, (60, 50, 44), (cx + k, GROUND - 60), (cx + k, GROUND), 2)
            pygame.draw.rect(surf, (60, 50, 44), (cx - 16, GROUND - 62, 32, 4))
            pygame.draw.rect(surf, (236, 190, 84), (cx - 16, GROUND - 62, 32, 4), 1)
        else:
            pygame.draw.line(surf, (60, 50, 44), (cx - 14, GROUND - 60), (cx - 14, GROUND), 2)
            pygame.draw.rect(surf, (60, 50, 44), (cx - 16, GROUND - 62, 14, 4))
        walking = self.t < 4.0
        name = "walk" if walking else ("bow" if self.t > 7.0 else "idle")
        img, (ax, ay) = gfx.frame("hero", hero, name, (self.t * 1.9) % 1, False)
        surf.blit(img, (int(self.hero_x) - ax, GROUND - ay))
        lname = "idle" if self.t < 6.0 else ("bow" if self.t > 7.0 else "walk")
        img, (ax, ay) = gfx.frame("lotus", lotus, lname if lname != "walk" else "idle", (self.t * 0.7) % 1, True)
        surf.blit(img, (int(self.lotus_x) - ax, GROUND - ay))
        if self.t > 4.2:
            gfx.text(surf, "THANK YOU, KAI!" if self.t < 7 else "...", 12, (int(self.lotus_x), GROUND - 66), (255, 190, 220),
                     outline=True)
        overlay(surf, 90 if self.t > 8 else 0)
        y0 = H - max(0.0, self.t - 8.0) * 13 if self.t > 8 else H + 40
        for i, s in enumerate(self.LINES + ["", "FINAL SCORE %06d" % self.score]):
            y = int(y0 + i * 14)
            if 20 < y < H - 6 and s:
                gfx.text(surf, s, 12, (W // 2, y), GOLD if "IRON" in s or "SCORE" in s else CREAM, outline=True)
