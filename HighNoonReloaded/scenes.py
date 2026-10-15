"""Game screens: title, controls, bounty ladder, outlaw intro, the duel, results and ending."""
import math
import random

import pygame
from pygame.locals import KEYDOWN, JOYBUTTONDOWN

import gfx
import inputs
from ai import CpuBrain
from config import (W, H, HUD_H, HORIZON, THEMES, LAYOUTS, LEVELS, SHERIFF, OUTLAW, GIRL, DIFFICULTY, CYLINDER,
                    RELOAD_TIME, ROUND_TIME, JAM_TIME, POINTS_CPU, AIM_ANGLES, POINTS_PVP, BULLET_MIN_Y, BULLET_MAX_Y,
                    PLAYER_MAX_Y)
from entities import Gunslinger, Bullet, Obstacle, Particle, FloatText

GOLD = (255, 220, 120)
CREAM = (255, 236, 200)
RED = (230, 70, 50)
DIM = (170, 140, 110)


class Scene:
    def __init__(self, app):
        self.app = app

    def handle(self, events):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


def overlay(surf, alpha=150, color=(10, 6, 4)):
    o = pygame.Surface((W, H), pygame.SRCALPHA)
    o.fill((*color, alpha))
    surf.blit(o, (0, 0))


def draw_menu(surf, items, sel, center, t, size=14, gap=13):
    cx, y = center
    for i, s in enumerate(items):
        yy = y + i * gap
        if i == sel:
            bob = int(math.sin(t * 8) * 1.5)
            gfx.text(surf, s, size, (cx, yy), GOLD, outline=True)
            w = gfx.text_width(s, size)
            gfx.text(surf, ">", size, (cx - w // 2 - 8 + bob, yy), GOLD, outline=True)
            gfx.text(surf, "<", size, (cx + w // 2 + 8 - bob, yy), GOLD, outline=True)
        else:
            gfx.text(surf, s, size, (cx, yy), DIM)


# =============================================================================
# Title
# =============================================================================
class TitleScene(Scene):
    ITEMS = ["1 PLAYER  -  BOUNTY HUNT", "2 PLAYERS  -  DUEL", "CONTROLS", "QUIT"]

    def __init__(self, app, sel=0):
        super().__init__(app)
        self.theme = THEMES["sunset"]
        self.bg = gfx.build_background(self.theme, seed=7)
        self.clouds = gfx.make_clouds(self.theme, random.Random(7))
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self.sel = sel
        self.t = 0.0
        self.left = Gunslinger(0, SHERIFF)
        self.right = Gunslinger(1, OUTLAW)
        self.left.x, self.left.y = 52, 206
        self.right.x, self.right.y = 348, 206
        self.tumble = Obstacle("tumble", 0, 0)
        self.title = gfx.fancy_text("HIGH NOON", 64, (255, 236, 130), (232, 104, 30), thick=2)
        self.sub = gfx.fancy_text("R E L O A D E D", 18, (255, 255, 255), (190, 196, 220), thick=1)
        self.twitch = 2.0
        app.audio.stop_wind()
        app.audio.play_music()

    def handle(self, events):
        for e in events:
            a = inputs.menu_action(e)
            if a in ("up", "down"):
                self.sel = (self.sel + (1 if a == "down" else -1)) % len(self.ITEMS)
                self.app.audio.play("blip")
            elif a == "ok":
                self.app.audio.play("select")
                if self.sel == 0:
                    self.app.change(LadderScene(self.app))
                elif self.sel == 1:
                    self.app.change(DuelScene(self.app, "pvp"))
                elif self.sel == 2:
                    self.app.change(ControlsScene(self.app))
                else:
                    self.app.quit()
            elif a == "back":
                self.app.quit()

    def update(self, dt):
        self.t += dt
        self.tumble.update(dt)
        for c in self.clouds:
            c[0] = (c[0] + c[2] * dt) % (W + 60)
        self.twitch -= dt
        if self.twitch <= 0:
            self.twitch = random.uniform(1.5, 3.5)
            random.choice((self.left, self.right)).shoot_t = 0.5
        self.left.update(dt, 0, 0)
        self.right.update(dt, 0, 0)

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        for x, y, _, img in self.clouds:
            surf.blit(img, (int(x) - 60, int(y)))
        gfx.draw_clock(surf, 11, 59)
        self.layer.fill((0, 0, 0, 0))
        self.tumble.draw(self.layer)
        self.left.draw(self.layer)
        self.right.draw(self.layer)
        self.layer.fill(self.theme["tint"], special_flags=pygame.BLEND_RGB_MULT)
        surf.blit(self.layer, (0, 0))

        bob = int(math.sin(self.t * 1.6) * 2)
        surf.blit(self.title, self.title.get_rect(center=(W // 2, 44 + bob)))
        surf.blit(self.sub, self.sub.get_rect(center=(W // 2, 74 + bob)))

        panel = pygame.Rect(0, 0, 196, 70)
        panel.center = (W // 2, 140)
        gfx.wood_panel(surf, panel)
        draw_menu(surf, self.ITEMS, self.sel, (W // 2, panel.y + 14), self.t)

        got = self.app.save.get("unlocked", 1) - 1
        gfx.text(surf, "BOUNTIES COLLECTED: %d / 7" % min(7, got), 12, (W // 2, 186), CREAM, outline=True)
        gfx.text(surf, "F11 FULLSCREEN   -   ESC QUIT", 11, (W // 2, 212), DIM, outline=True)


# =============================================================================
# Controls
# =============================================================================
class ControlsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = gfx.build_background(THEMES["noon"], seed=11)
        self.t = 0.0

    def handle(self, events):
        for e in events:
            if inputs.menu_action(e) in ("ok", "back"):
                self.app.audio.play("blip")
                self.app.change(TitleScene(self.app, sel=2))

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        overlay(surf, 120)
        panel = pygame.Rect(16, 14, W - 32, H - 28)
        gfx.wood_panel(surf, panel)
        surf.blit(t := gfx.fancy_text("CONTROLS", 30, (255, 236, 130), (232, 104, 30)), t.get_rect(center=(W // 2, 30)))
        rows = [
            ("", "PLAYER 1  (SHERIFF)", "PLAYER 2  (OUTLAW)"),
            ("MOVE", "W  A  S  D", "ARROW KEYS"),
            ("FIRE UP", "R", "I"),
            ("FIRE STRAIGHT", "F", "K"),
            ("FIRE DOWN", "V", ",  (COMMA)"),
            ("GAMEPAD", "STICK/D-PAD + A, Y, B", "SECOND GAMEPAD"),
        ]
        y = 56
        for label, a, b in rows:
            col = GOLD if not label else CREAM
            gfx.text(surf, label, 12, (34, y), DIM, anchor="midleft")
            gfx.text(surf, a, 12, (190, y), col)
            gfx.text(surf, b, 12, (314, y), col)
            y += 15
        tips = ("IN 1 PLAYER MODE BOTH KEY SETS (AND SPACE) CONTROL THE SHERIFF. "
                "6 SHOTS PER CYLINDER, THEN A SLOW RELOAD. ANGLED SHOTS RICOCHET OFF THE FENCES. "
                "SHOOT BEFORE 'DRAW!' AND YOUR GUN JAMS. CACTI, BARRELS AND TUMBLEWEEDS CAN BE "
                "SHOT TO PIECES.  ESC / P = PAUSE")
        y += 6
        for s in gfx.wrap(tips, 12, panel.w - 24):
            gfx.text(surf, s, 11, (W // 2, y), CREAM)
            y += 11
        if int(self.t * 2) % 2 == 0:
            gfx.text(surf, "PRESS FIRE TO RETURN", 12, (W // 2, H - 24), GOLD, outline=True)


# =============================================================================
# Bounty ladder (level select)
# =============================================================================
class LadderScene(Scene):
    def __init__(self, app, sel=None):
        super().__init__(app)
        self.bg = gfx.build_background(THEMES["afternoon"], seed=5)
        self.unlocked = max(1, min(7, app.save.get("unlocked", 1)))
        self.sel = self.unlocked - 1 if sel is None else sel
        self.t = 0.0
        app.audio.play_music()

    def handle(self, events):
        for e in events:
            a = inputs.menu_action(e)
            if a in ("left", "right"):
                n = self.sel + (1 if a == "right" else -1)
                if 0 <= n < 7:
                    self.sel = n
                    self.app.audio.play("blip")
            elif a == "ok":
                if self.sel < self.unlocked:
                    self.app.audio.play("select")
                    self.app.change(IntroScene(self.app, self.sel))
                else:
                    self.app.audio.play("jam")
            elif a == "back":
                self.app.audio.play("blip")
                self.app.change(TitleScene(self.app, sel=0))

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        overlay(surf, 90)
        t = gfx.fancy_text("THE BOUNTY BOARD", 30, (255, 236, 130), (232, 104, 30))
        surf.blit(t, t.get_rect(center=(W // 2, 22)))
        board = pygame.Rect(8, 40, W - 16, 86)
        gfx.wood_panel(surf, board)
        pw, ph, gap = 50, 74, 4
        x0 = (W - (7 * pw + 6 * gap)) // 2
        for i, lv in enumerate(LEVELS):
            r = pygame.Rect(x0 + i * (pw + gap), board.y + 6, pw, ph)
            if i == self.sel:
                r.y -= 2 + int(abs(math.sin(self.t * 4)) * 2)
            gfx.draw_poster(surf, r, lv["char"], lv["bounty"], locked=i >= self.unlocked, name_size=8)
            if i < self.unlocked - 1:
                stamp = gfx.font(14).render("PAID", False, (190, 30, 20))
                stamp = pygame.transform.rotate(stamp, 20)
                surf.blit(stamp, stamp.get_rect(center=(r.centerx, r.y + 30)))
            if i == self.sel:
                pygame.draw.rect(surf, GOLD, r.inflate(4, 4), 1)

        lv = LEVELS[self.sel]
        info = pygame.Rect(30, 134, W - 60, 72)
        gfx.wood_panel(surf, info)
        if self.sel < self.unlocked:
            gfx.text(surf, "%d.  %s" % (self.sel + 1, lv["char"]["name"]), 16, (W // 2, info.y + 12), GOLD, outline=True)
            gfx.text(surf, "%s   -   REWARD $%d" % (lv["title"], lv["bounty"]), 12, (W // 2, info.y + 27), CREAM)
            danger = "DANGER: %s" % DIFFICULTY[self.sel]
            if lv.get("boss"):
                danger += "   -   BOSS (%d HITS)" % lv["char"]["hp"]
            gfx.text(surf, danger, 12, (W // 2, info.y + 40), RED if lv.get("boss") else CREAM)
            for k in range(7):
                gfx.star(surf, W // 2 - 36 + k * 12, info.y + 54, k <= self.sel)
        else:
            gfx.text(surf, "%d.  ??????" % (self.sel + 1), 16, (W // 2, info.y + 16), DIM, outline=True)
            gfx.text(surf, "COLLECT THE PREVIOUS BOUNTY FIRST.", 12, (W // 2, info.y + 38), CREAM)
        gfx.text(surf, "LEFT / RIGHT  CHOOSE     FIRE  RIDE OUT     ESC  BACK", 11, (W // 2, H - 10), DIM, outline=True)


# =============================================================================
# Outlaw intro card
# =============================================================================
class IntroScene(Scene):
    def __init__(self, app, level):
        super().__init__(app)
        self.level = level
        self.lv = LEVELS[level]
        self.bg = gfx.build_background(THEMES[self.lv["theme"]], seed=100 + level)
        self.t = 0.0

    def handle(self, events):
        for e in events:
            a = inputs.menu_action(e)
            if a == "ok" and self.t > 0.4:
                self.app.audio.play("select")
                self.app.change(DuelScene(self.app, "cpu", self.level))
            elif a == "back":
                self.app.audio.play("blip")
                self.app.change(LadderScene(self.app, self.level))

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        overlay(surf, 110)
        lv = self.lv
        slide = max(0, int((0.35 - self.t) * 500))
        poster = pygame.Rect(24 - slide, 26, 120, 168)
        gfx.draw_poster(surf, poster, lv["char"], lv["bounty"], big=True, name_size=12)
        gfx.text(surf, "DEAD OR ALIVE", 12, (poster.centerx, poster.bottom - 30), (90, 50, 30), shadow=None)

        x = 166 + slide
        gfx.text(surf, "OUTLAW %d OF 7" % (self.level + 1), 12, (x, 36), DIM, anchor="midleft", outline=True)
        nm = gfx.fancy_text(lv["char"]["name"], 30, (255, 236, 130), (232, 104, 30))
        surf.blit(nm, nm.get_rect(midleft=(x - 2, 56)))
        gfx.text(surf, lv["title"], 14, (x, 78), CREAM, anchor="midleft", outline=True)
        gfx.text(surf, "DANGER:  " + DIFFICULTY[self.level], 12, (x, 96), CREAM, anchor="midleft", outline=True)
        for k in range(7):
            gfx.star(surf, x + 4 + k * 12, 110, k <= self.level)
        q = pygame.Rect(x - 4, 122, W - x - 10, 34)
        gfx.wood_panel(surf, q)
        lines = gfx.wrap('"%s"' % lv["quote"], 12, q.w - 12)
        for k, line in enumerate(lines):
            gfx.text(surf, line, 12, (q.centerx, q.centery + (k - (len(lines) - 1) / 2) * 10), GOLD)
        if lv.get("boss"):
            for k, line in enumerate(gfx.wrap(lv["boss_note"], 12, W - x - 10)):
                gfx.text(surf, line, 12, (x, 164 + k * 10), RED, anchor="midleft", outline=True)
        else:
            gfx.text(surf, "FIRST TO %d WINS.  AT HIGH NOON." % POINTS_CPU, 12, (x, 168), CREAM,
                     anchor="midleft", outline=True)
        if int(self.t * 2.5) % 2 == 0:
            gfx.text(surf, "PRESS FIRE TO DUEL", 14, (x + 90, 196), GOLD, outline=True)


# =============================================================================
# The duel
# =============================================================================
class DuelScene(Scene):
    def __init__(self, app, mode, level=0, demo_levels=(3, 3)):
        super().__init__(app)
        self.mode = mode           # "cpu", "pvp" or "demo" (CPU vs CPU, used for testing)
        self.level = level
        rnd = random.Random()
        if mode == "cpu":
            self.cfg = LEVELS[level]
            theme_key, layout, p2 = self.cfg["theme"], LAYOUTS[self.cfg["layout"]], self.cfg["char"]
            self.target = POINTS_CPU
        else:
            self.cfg = None
            theme_key, layout, p2 = rnd.choice(list(THEMES)), rnd.choice(LAYOUTS), OUTLAW
            self.target = POINTS_PVP if mode == "pvp" else POINTS_CPU
        self.theme = THEMES[theme_key]
        self.tint = self.theme.get("tint")
        self.bg = gfx.build_background(self.theme, seed=rnd.randrange(1 << 30))
        self.clouds = gfx.make_clouds(self.theme, rnd)
        self.dust = ([[rnd.uniform(0, W), rnd.uniform(HORIZON, H), rnd.uniform(80, 170), rnd.randint(2, 7)]
                      for _ in range(70)] if self.theme.get("dust") else [])
        self.layout = layout
        self.players = [Gunslinger(0, SHERIFF), Gunslinger(1, p2)]
        p0, p1 = self.players
        self.brains = [None, None]
        self.speed = [1.0, 1.0]
        if mode == "cpu":
            self.brains[1] = CpuBrain(self.cfg, p1, p0)
            self.speed[1] = self.cfg["speed"]
        elif mode == "demo":
            a, b = LEVELS[demo_levels[0]], LEVELS[demo_levels[1]]
            self.brains = [CpuBrain(a, p0, p1), CpuBrain(b, p1, p0)]
            self.speed = [a["speed"], b["speed"]]
        if mode == "pvp":
            self.names = ["PLAYER 1", "PLAYER 2"]
        else:
            self.names = [SHERIFF["name"], p2["name"]]
        self.scores = [0, 0]
        self.round_no = 0
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self.hud = gfx.hud_bar()
        self.flash_imgs = (gfx.muzzle_flash(1), gfx.muzzle_flash(-1))
        self.stats = {"shots": [0, 0], "hits": [0, 0]}
        self.paused = False
        self.pause_sel = 0
        self.fire_queue = []
        self.match_winner = None
        app.audio.stop_music()
        app.audio.start_wind()
        self.start_round()

    # ----------------------------------------------------------------- rounds
    def start_round(self):
        self.round_no += 1
        for p in self.players:
            p.reset()
            p.y = random.uniform(120, 190)
        self.obstacles = [Obstacle(*spec) for spec in self.layout]
        self.bullets = []
        self.particles = []
        self.texts = []
        self.flashes = []
        for b in self.brains:
            if b:
                b.reset()
        self.state = "ready"
        self.state_t = 0.0
        self.draw_at = 2.6 + random.uniform(0.0, 0.9)
        self.cues = [False, False]
        self.round_clock = ROUND_TIME
        self.decided = False
        self.slowmo = 0.0
        self.shake = 0.0
        self.flash = 0.0
        self.banner = ("ROUND %d" % self.round_no, 1.0)

    def end_round(self, winner, msg):
        self.state = "roundover"
        self.state_t = 0.0
        self.decided = True
        if winner is not None:
            self.scores[winner] += 1
        self.banner = (msg, 2.6)
        if max(self.scores) >= self.target:
            self.match_winner = 0 if self.scores[0] >= self.target else 1

    # ------------------------------------------------------------------ input
    def handle(self, events):
        for e in events:
            if self.paused:
                a = inputs.menu_action(e)
                if a in ("up", "down"):
                    self.pause_sel ^= 1
                    self.app.audio.play("blip")
                elif a == "ok":
                    if self.pause_sel == 0:
                        self.paused = False
                    else:
                        self.app.change(TitleScene(self.app))
                elif a == "back":
                    self.paused = False
                continue
            if inputs.is_pause(e):
                self.paused = True
                self.pause_sel = 0
                self.app.audio.play("blip")
                continue
            if e.type == KEYDOWN:
                if self.mode == "cpu":
                    aim = inputs.SOLO_FIRE.get(e.key)
                    if aim:
                        self.fire_queue.append((0, aim))
                elif self.mode == "pvp":
                    if e.key in inputs.P1_FIRE:
                        self.fire_queue.append((0, inputs.P1_FIRE[e.key]))
                    elif e.key in inputs.P2_FIRE:
                        self.fire_queue.append((1, inputs.P2_FIRE[e.key]))
            elif e.type == JOYBUTTONDOWN and e.button in inputs.JOY_FIRE:
                idx = self.app.joy_index(e.instance_id)
                if self.mode == "cpu":
                    idx = 0
                if idx in (0, 1) and self.mode != "demo":
                    self.fire_queue.append((idx, inputs.JOY_FIRE[e.button]))

    def _human_move(self, i):
        keys = pygame.key.get_pressed()
        joys = self.app.joysticks
        if self.mode == "cpu":
            return inputs.move_vector(keys, (inputs.P1_MOVE, inputs.P2_MOVE), joys)
        maps = (inputs.P1_MOVE,) if i == 0 else (inputs.P2_MOVE,)
        return inputs.move_vector(keys, maps, joys[i:i + 1])

    # ---------------------------------------------------------------- effects
    def puff(self, x, y, n=4, color=(200, 190, 170)):
        for _ in range(n):
            self.particles.append(Particle(x, y, random.uniform(-8, 8), random.uniform(-14, -4),
                                           random.uniform(0.4, 0.9), color, size=random.randint(1, 2),
                                           kind="smoke", drag=1.5))

    def sparks(self, x, y, n=6, color=(255, 220, 120), dirx=0):
        for _ in range(n):
            self.particles.append(Particle(x, y, random.uniform(-50, 50) + dirx * 40, random.uniform(-60, 20),
                                           random.uniform(0.15, 0.4), color, grav=200))

    def shoot(self, p, aim):
        b = p.fire(aim)
        self.bullets.append(b)
        if p.char.get("twin"):          # Two-Gun Rosa fires both revolvers
            b2 = Bullet(b.x - 2 * p.facing, b.y + 1, AIM_ANGLES[aim], p.facing, p.side)
            self.bullets.append(b2)
        self.stats["shots"][p.side] += 1
        self.app.audio.play("shot", 0.8)
        self.flashes.append([b.x, b.y, 0.07, p.facing])
        self.puff(b.x, b.y, 3, (220, 220, 220))
        self.shake = max(self.shake, 1.0)

    def wound(self, victim, bullet):
        """A boss soaks up a hit: knock back, flash, and get angrier."""
        victim.wound()
        self.stats["hits"][bullet.owner] += 1
        d = 1 if bullet.vx > 0 else -1
        box = victim.hitbox()
        horse = victim.char.get("body") == "mounted" and bullet.y > box.top + 16
        self.app.audio.play("hit", 0.6)
        self.app.audio.play("neigh" if horse else "grunt", 0.8)
        self.shake = max(self.shake, 3.5)
        self.slowmo = max(self.slowmo, 0.25)
        for _ in range(8):
            self.particles.append(Particle(bullet.x, bullet.y, d * random.uniform(20, 70), random.uniform(-60, 0),
                                           random.uniform(1.0, 2.0), random.choice(((150, 20, 20), (110, 10, 14))),
                                           grav=260, floor=victim.y + random.uniform(-2, 3)))
        word = "NEIGH!" if horse else random.choice(("ARGH!", "OOF!", "GRRR!"))
        self.texts.append(FloatText(victim.x, box.top - 6, word, (255, 150, 60), 0.9, 14))
        brain = self.brains[victim.side]
        if brain:
            brain.enrage()
            self.texts.append(FloatText(victim.x, box.top - 18, "ENRAGED!", (255, 70, 50), 1.1))

    def kill(self, victim, bullet):
        victim.alive = False
        self.stats["hits"][bullet.owner] += 1
        self.app.audio.play("hit")
        self.shake = 6.0
        self.slowmo = 1.0
        d = 1 if bullet.vx > 0 else -1
        for _ in range(14):
            self.particles.append(Particle(bullet.x, bullet.y, d * random.uniform(20, 90), random.uniform(-70, 10),
                                           random.uniform(1.5, 3.0), random.choice(((150, 20, 20), (110, 10, 14))),
                                           grav=260, floor=victim.y + random.uniform(-2, 3)))
        hat = victim.frames["hat"][0 if victim.facing > 0 else 1]
        self.particles.append(Particle(victim.x, victim.y + victim.geom["hat_y"], d * 40, -110, 3.0,
                                       kind="img", img=hat,
                                       grav=300, vr=-d * 540, floor=victim.y + 2))
        self.texts.append(FloatText(victim.x, victim.y - 34, "BANG!", (255, 90, 60), 1.2, 16))
        w = bullet.owner
        if self.mode == "pvp":
            msg = "PLAYER %d WINS THE ROUND" % (w + 1)
        elif self.mode == "cpu":
            msg = "GOT 'IM!" if w == 0 else "YOU'RE HIT!"
        else:
            msg = "%s WINS" % self.names[w]
        self.end_round(w, msg)

    # ----------------------------------------------------------------- update
    def update(self, dt):
        if self.paused:
            return
        if self.slowmo > 0:
            self.slowmo -= dt
            dt *= 0.3
        self.shake = max(0.0, self.shake - dt * 20)
        self.flash = max(0.0, self.flash - dt)
        self.state_t += dt
        for c in self.clouds:
            c[0] = (c[0] + c[2] * dt) % (W + 60)
        for d in self.dust:
            d[0] += d[2] * dt
            if d[0] > W + 10:
                d[0] = -10
                d[1] = random.uniform(HORIZON, H)
        if self.banner:
            s, t = self.banner
            self.banner = (s, t - dt) if t - dt > 0 else None

        st = self.state
        active = st in ("ready", "fight")

        # queued human trigger pulls
        for idx, aim in self.fire_queue:
            p = self.players[idx]
            if not p.alive or not active:
                continue
            if st == "ready":
                if p.jam_t <= 0:
                    p.jam_t = (self.draw_at - self.state_t) + JAM_TIME
                    self.app.audio.play("jam")
                    self.texts.append(FloatText(p.x, p.y - 32, "TOO EARLY!", (255, 160, 80), 1.2))
            elif p.jam_t > 0:
                pass
            elif p.reload_t > 0 or p.ammo <= 0:
                self.app.audio.play("click", 0.6)
            elif p.cool <= 0:
                self.shoot(p, aim)
        self.fire_queue.clear()

        for i, p in enumerate(self.players):
            brain = self.brains[i]
            if brain:
                mx, my, aim = brain.update(dt, self)
                if aim and st == "fight" and p.can_fire():
                    self.shoot(p, aim)
            else:
                mx, my = self._human_move(i)
            if not active:
                mx = my = 0.0
            for ev in p.update(dt, mx, my, self.speed[i]):
                if ev == "reloaded":
                    self.app.audio.play("reload", 0.7)
                elif ev == "step":
                    self.puff(p.x - 3 * p.facing, p.y, 1, shade_dust(self.theme))

        for o in self.obstacles:
            o.update(dt)
        self._update_bullets(dt)
        self.particles = [pt for pt in self.particles if pt.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]
        for f in self.flashes:
            f[2] -= dt
        self.flashes = [f for f in self.flashes if f[2] > 0]

        if st == "ready":
            if not self.cues[0] and self.state_t >= 1.0:
                self.cues[0] = True
                self.app.audio.play("tick")
                self.banner = ("READY...", 0.8)
            if not self.cues[1] and self.state_t >= 1.8:
                self.cues[1] = True
                self.app.audio.play("tick")
                self.banner = ("STEADY...", 0.8)
            if self.state_t >= self.draw_at:
                self.state = "fight"
                self.state_t = 0.0
                self.app.audio.play("bell", 0.8)
                self.banner = ("DRAW!", 0.9)
                self.flash = 0.12
        elif st == "fight":
            self.round_clock -= dt
            if self.round_clock <= 0:
                self.round_clock = 0
                self.end_round(None, "SUNDOWN - NOBODY WINS")
        elif st == "roundover" and self.state_t > 2.8:
            if self.match_winner is not None:
                self.finish()
            else:
                self.start_round()

    def _update_bullets(self, dt):
        for b in self.bullets:
            b.age += dt
            dist = math.hypot(b.vx, b.vy) * dt
            n = max(1, int(dist / 2) + 1)
            sx, sy = b.vx * dt / n, b.vy * dt / n
            target = self.players[1 - b.owner]
            for _ in range(n):
                b.x += sx
                b.y += sy
                if b.y < BULLET_MIN_Y or b.y > BULLET_MAX_Y:
                    lim = BULLET_MIN_Y if b.y < BULLET_MIN_Y else BULLET_MAX_Y
                    b.y = 2 * lim - b.y
                    b.vy = -b.vy
                    sy = -sy
                    b.bounces += 1
                    self.app.audio.play("ricochet", 0.45)
                    self.sparks(b.x, lim, 5)
                ix, iy = int(b.x), int(b.y)
                for o in self.obstacles:
                    if o.active and o.rect.collidepoint(ix, iy):
                        b.alive = False
                        destroyed = o.damage()
                        self._impact(o, b, destroyed)
                        break
                if not b.alive:
                    break
                if (not self.decided and target.alive and target.invuln <= 0
                        and target.hitbox().collidepoint(ix, iy)):
                    b.alive = False
                    if target.hp > 1:
                        self.wound(target, b)
                    else:
                        self.kill(target, b)
                    break
                if b.x < -6 or b.x > W + 6:
                    b.alive = False
                    break
            b.trail.append((b.x, b.y))
            if len(b.trail) > 6:
                b.trail.pop(0)
        self.bullets = [b for b in self.bullets if b.alive]

    def _impact(self, o, b, destroyed):
        k = o.kind
        d = -1 if b.vx > 0 else 1
        if k == "cactus":
            self.app.audio.play("chip", 0.7)
            col = ((64, 150, 62), (128, 200, 98))
        elif k in ("barrel", "wagon", "coach", "tumble"):
            self.app.audio.play("wood", 0.7)
            col = ((150, 95, 50), (200, 160, 100))
        else:
            self.app.audio.play("ricochet", 0.3)
            col = ((180, 170, 160), (255, 230, 150))
        n = 16 if destroyed else 6
        for _ in range(n):
            self.particles.append(Particle(b.x, b.y, d * random.uniform(10, 70), random.uniform(-80, 0),
                                           random.uniform(0.6, 1.4), random.choice(col), size=random.choice((1, 1, 2)),
                                           grav=260, floor=o.sort_y + random.uniform(-2, 4)))
        if destroyed:
            self.puff(o.x, o.sort_y - 6, 6, (200, 180, 140))
            self.shake = max(self.shake, 2.5)

    def finish(self):
        self.app.audio.stop_wind()
        if self.mode == "demo":
            self.app.change(DuelScene(self.app, "demo"))
            return
        self.app.change(ResultScene(self.app, self.mode, self.level, self.match_winner, self.stats,
                                    self.scores, self.names))

    # ------------------------------------------------------------------- draw
    def draw(self, surf):
        sh = self.shake
        ox = int(random.uniform(-sh, sh)) if sh > 0.5 else 0
        oy = int(random.uniform(-sh, sh)) if sh > 0.5 else 0
        surf.blit(self.bg, (ox, oy))
        for x, y, _, img in self.clouds:
            surf.blit(img, (int(x) - 60 + ox, int(y) + oy))
        if self.state == "ready":
            m = 58 + 2 * min(1.0, self.state_t / self.draw_at)
            gfx.draw_clock(surf, 11 if m < 60 else 12, m % 60)
        else:
            gfx.draw_clock(surf, 12, min(59, (ROUND_TIME - self.round_clock) / ROUND_TIME * 15))

        L = self.layer
        L.fill((0, 0, 0, 0))
        ents = [(o.sort_y, 0, o) for o in self.obstacles if o.active] + [(p.y, 1, p) for p in self.players]
        ents.sort(key=lambda e: (e[0], e[1]))
        for _, _, e in ents:
            e.draw(L, ox, oy)
        for pt in self.particles:
            pt.draw(L, ox, oy)
        for b in self.bullets:
            b.draw(L, ox, oy)
        for x, y, _, facing in self.flashes:
            img = self.flash_imgs[0 if facing > 0 else 1]
            L.blit(img, img.get_rect(center=(int(x) + ox + 3 * facing, int(y) + oy)))
        if self.tint:
            L.fill(self.tint, special_flags=pygame.BLEND_RGB_MULT)
        surf.blit(L, (0, 0))

        if self.theme.get("lights"):
            for b in self.bullets:
                g = gfx.glow(6, (120, 90, 40))
                surf.blit(g, (int(b.x) - 6 + ox, int(b.y) - 6 + oy), special_flags=pygame.BLEND_RGB_ADD)
            for x, y, _, _ in self.flashes:
                g = gfx.glow(18, (200, 150, 60))
                surf.blit(g, (int(x) - 18 + ox, int(y) - 18 + oy), special_flags=pygame.BLEND_RGB_ADD)
        if self.dust:
            for x, y, _, ln in self.dust:
                pygame.draw.line(surf, (236, 200, 140), (int(x), int(y)), (int(x) + ln, int(y)))
            overlay(surf, 38, (220, 170, 110))

        for t in self.texts:
            t.draw(surf)
        self.draw_hud(surf)
        self.draw_banner(surf)
        if self.flash > 0:
            overlay(surf, int(200 * self.flash / 0.12), (255, 250, 230))
        if self.paused:
            overlay(surf, 160)
            panel = pygame.Rect(0, 0, 150, 64)
            panel.center = (W // 2, H // 2)
            gfx.wood_panel(surf, panel)
            gfx.text(surf, "PAUSED", 16, (W // 2, panel.y + 14), CREAM, outline=True)
            draw_menu(surf, ["RESUME", "QUIT TO TITLE"], self.pause_sel, (W // 2, panel.y + 34), self.state_t)

    def draw_hud(self, surf):
        surf.blit(self.hud, (0, 0))
        for i, p in enumerate(self.players):
            left = i == 0
            x = 6 if left else W - 6
            anchor = "midleft" if left else "midright"
            gfx.text(surf, self.names[i], 11, (x, 5), CREAM, anchor=anchor)
            # cylinder
            for k in range(CYLINDER):
                bx = x + k * 4 if left else x - 2 - k * 4
                gfx.bullet_icon(surf, bx, 11, k < p.ammo)
            if p.reload_t > 0:
                frac = 1 - p.reload_t / RELOAD_TIME
                rx = x if left else x - 23
                surf.fill((40, 24, 14), (rx, 17, 23, 2))
                surf.fill((250, 210, 90), (rx, 17, int(23 * frac), 2))
            # score stars
            for k in range(self.target):
                sx = (x + 34 + k * 10) if left else (x - 34 - k * 10)
                gfx.star(surf, sx, 13, k < self.scores[i])
        for p in self.players:
            if p.max_hp > 1:
                self.draw_boss_bar(surf, p)
        mins = int(self.round_clock) // 60
        secs = int(self.round_clock) % 60
        gfx.text(surf, "ROUND %d" % self.round_no, 10, (W // 2, 6), DIM)
        col = RED if self.round_clock < 10 and self.state == "fight" else GOLD
        gfx.text(surf, "%d:%02d" % (mins, secs), 12, (W // 2, 14), col)
        if self.mode == "cpu":
            gfx.text(surf, "OUTLAW %d/7" % (self.level + 1), 10, (W // 2 + 58, 10), DIM)

    def draw_boss_bar(self, surf, p):
        w, h = 104, 6
        cx = W - 64 if p.side == 1 else 64
        r = pygame.Rect(0, 0, w, h)
        r.midtop = (cx, HUD_H + 4)
        gfx.text(surf, "BOSS", 10, (r.x - 3, r.centery), (255, 90, 60), anchor="midright", outline=True)
        surf.fill((20, 8, 6), r.inflate(4, 4))
        surf.fill((70, 20, 16), r)
        ghost = int(w * p.hp_shown / p.max_hp)
        surf.fill((250, 230, 150), (r.x, r.y, ghost, h))
        cur = int(w * p.hp / p.max_hp)
        if cur:
            pulse = 30 if p.hp == 1 and int(self.state_t * 6) % 2 else 0
            surf.fill((min(255, 210 + pulse), 40, 30), (r.x, r.y, cur, h))
            surf.fill((255, 130, 100), (r.x, r.y, cur, 1))
            surf.fill((130, 20, 16), (r.x, r.bottom - 1, cur, 1))
        for k in range(1, p.max_hp):
            sx = r.x + w * k // p.max_hp
            surf.fill((20, 8, 6), (sx, r.y, 1, h))
        pygame.draw.rect(surf, (250, 210, 90), r.inflate(4, 4), 1)

    def draw_banner(self, surf):
        if not self.banner:
            return
        s, t = self.banner
        if s == "DRAW!":
            img = gfx.fancy_text(s, 64, (255, 250, 200), (240, 80, 30), thick=3)
            k = 1 + max(0.0, t - 0.7) * 2
            if k != 1:
                img = pygame.transform.scale(img, (int(img.get_width() * k), int(img.get_height() * k)))
        elif s.startswith(("READY", "STEADY", "ROUND")):
            img = gfx.fancy_text(s, 36, (255, 236, 160), (220, 120, 40))
        else:
            img = gfx.fancy_text(s, 30, (255, 236, 160), (220, 120, 40))
        surf.blit(img, img.get_rect(center=(W // 2, 104)))
        if self.state == "roundover":
            plate = pygame.Rect(0, 0, 64, 18)
            plate.center = (W // 2, 128)
            gfx.wood_panel(surf, plate)
            gfx.text(surf, "%d  -  %d" % tuple(self.scores), 16, plate.center, GOLD, outline=True)


def shade_dust(theme):
    return gfx.shade(theme["ground"][0], 1.08)


# =============================================================================
# Results
# =============================================================================
class ResultScene(Scene):
    def __init__(self, app, mode, level, winner, stats, scores, names):
        super().__init__(app)
        self.mode, self.level, self.winner = mode, level, winner
        self.stats, self.scores, self.names = stats, scores, names
        self.t = 0.0
        self.sel = 0
        self.won = mode == "cpu" and winner == 0
        theme = "sunset" if self.won or mode == "pvp" else "dusk"
        self.bg = gfx.build_background(THEMES[theme], seed=21)
        if mode == "cpu":
            if self.won:
                self.items = ["THE END" if level == 6 else "NEXT OUTLAW", "BOUNTY BOARD", "TITLE"]
                save = app.save
                save["unlocked"] = max(save.get("unlocked", 1), min(8, level + 2))
                beaten = set(save.get("beaten", []))
                if level not in beaten:
                    save["bounty"] = save.get("bounty", 0) + LEVELS[level]["bounty"]
                beaten.add(level)
                save["beaten"] = sorted(beaten)
                app.write_save()
                app.audio.play("win")
            else:
                self.items = ["TRY AGAIN", "BOUNTY BOARD", "TITLE"]
                app.audio.play("lose")
        else:
            self.items = ["REMATCH", "TITLE"]
            app.audio.play("win")
        self.winner_sprite = Gunslinger(winner, SHERIFF if winner == 0 else (
            LEVELS[level]["char"] if mode == "cpu" else OUTLAW))
        self.winner_sprite.x, self.winner_sprite.y = W // 2, 132
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)

    def handle(self, events):
        for e in events:
            a = inputs.menu_action(e)
            if a in ("up", "down") and self.t > 0.5:
                self.sel = (self.sel + (1 if a == "down" else -1)) % len(self.items)
                self.app.audio.play("blip")
            elif a == "ok" and self.t > 0.8:
                self.app.audio.play("select")
                choice = self.items[self.sel]
                if choice == "NEXT OUTLAW":
                    self.app.change(IntroScene(self.app, self.level + 1))
                elif choice == "THE END":
                    self.app.change(EndingScene(self.app))
                elif choice == "TRY AGAIN":
                    self.app.change(DuelScene(self.app, "cpu", self.level))
                elif choice == "REMATCH":
                    self.app.change(DuelScene(self.app, "pvp"))
                elif choice == "BOUNTY BOARD":
                    self.app.change(LadderScene(self.app, min(6, self.level + (1 if self.won else 0))))
                else:
                    self.app.change(TitleScene(self.app))

    def update(self, dt):
        self.t += dt
        p = self.winner_sprite
        p.update(dt, 0, 0)
        if int(self.t * 10) % 25 == 0:
            p.shoot_t = 0.3
            p.aim = "up"

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        overlay(surf, 70)
        if self.mode == "cpu":
            head = "BOUNTY COLLECTED!" if self.won else "PUSHIN' UP DAISIES"
            sub = ("$%d REWARD FOR %s" % (LEVELS[self.level]["bounty"], LEVELS[self.level]["char"]["name"])
                   if self.won else "%s GOT THE DRAW ON YOU." % LEVELS[self.level]["char"]["name"])
        else:
            head = "PLAYER %d WINS!" % (self.winner + 1)
            sub = "FASTEST GUN IN TOWN - %d TO %d" % (max(self.scores), min(self.scores))
        img = gfx.fancy_text(head, 40, (255, 240, 150), (230, 100, 30) if self.won or self.mode == "pvp"
                             else (150, 40, 40))
        surf.blit(img, img.get_rect(center=(W // 2, 34)))
        gfx.text(surf, sub, 13, (W // 2, 62), CREAM, outline=True)
        self.layer.fill((0, 0, 0, 0))
        self.winner_sprite.draw(self.layer)
        big = pygame.transform.scale(self.layer, (W * 2, H * 2))
        surf.blit(big, (-W // 2, -H // 2 + 6))
        y = 150
        for i in range(2):
            shots, hits = self.stats["shots"][i], self.stats["hits"][i]
            acc = int(100 * hits / shots) if shots else 0
            gfx.text(surf, "%s:  %d SHOTS, %d HITS, %d%% ACCURACY" % (self.names[i], shots, hits, acc), 11,
                     (W // 2, y), DIM, outline=True)
            y += 11
        panel = pygame.Rect(0, 0, 150, 14 + 12 * len(self.items))
        panel.midtop = (W // 2, 176)
        gfx.wood_panel(surf, panel)
        draw_menu(surf, self.items, self.sel, (W // 2, panel.y + 9), self.t, size=13, gap=12)


# =============================================================================
# Ending
# =============================================================================
class EndingScene(Scene):
    """The sheriff finds Miss Lily, and the two ride off into the sunset while the credits roll."""
    LINES = ["THE WEST IS QUIET AGAIN.", "", "SEVEN OUTLAWS. SEVEN DRAWS.", "ONE SHERIFF STILL STANDING.", "",
             "AND MISS LILY, SAVED FROM", "EL DIABLO'S CLUTCHES,", "RODE WITH HIM INTO THE SUNSET.", "",
             "THEY'LL SING ABOUT SHERIFF COLE", "IN EVERY SALOON FROM HERE", "TO THE PACIFIC.", "", "",
             "HIGH NOON: RELOADED", "", "A TRIBUTE TO THE 8-BIT DUELS", "OF THE ZX SPECTRUM ERA", "", "",
             "THANKS FOR PLAYING, PARTNER."]
    CREDITS = ["AI Developer: Alexandru Frigioiu", "contact: alexandrufn@yahoo.com"]
    MOUNT_T, RIDE_T = 5.2, 19.0    # climb on the horse / reach the horizon

    def __init__(self, app):
        super().__init__(app)
        self.theme = THEMES["sunset"]
        self.bg = gfx.build_background(self.theme, seed=99)
        self.clouds = gfx.make_clouds(self.theme, random.Random(99))
        self.t = 0.0
        self.hero = Gunslinger(0, SHERIFF)
        self.hero.x, self.hero.y = 196, 206
        self.hero.zone = (0, W)
        self.girl = Gunslinger(1, GIRL)
        self.girl.x, self.girl.y = 300, 206
        self.girl.zone = (0, W)
        self.ride = gfx.build_couple_ride(SHERIFF, GIRL)
        self.particles = []
        self.texts = []
        self.mounted = False
        self.hearts = 0.0
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)
        app.audio.stop_wind()
        app.audio.play_music()
        total = app.save.get("bounty", 0)
        self.lines = ([(l, 13) for l in self.LINES] + [("", 13), ("TOTAL BOUNTY: $%d" % total, 13), ("", 13),
                      ("", 13)] + [(c, 14) for c in self.CREDITS])

    def handle(self, events):
        for e in events:
            if inputs.menu_action(e) in ("ok", "back") and self.t > 2:
                self.app.change(TitleScene(self.app))

    def _ride_pos(self):
        p = min(1.0, max(0.0, (self.t - self.MOUNT_T) / (self.RIDE_T - self.MOUNT_T)))
        e = p * p * (3 - 2 * p)
        x = 288 + (292 - 288) * e
        y = 206 + (HORIZON + 14 - 206) * (p ** 0.7)
        return x, y, 1.0 - 0.72 * p, p

    def update(self, dt):
        self.t += dt
        for c in self.clouds:
            c[0] = (c[0] + c[2] * dt) % (W + 60)
        if not self.mounted:
            walking = self.hero.x < self.girl.x - 16
            self.hero.update(dt, 0.6 if walking else 0, 0)
            self.girl.update(dt, 0, 0)
            if not walking and self.hearts == 0:
                self.hearts = 1.0
                self.app.audio.play("win", 0.6)
                self.texts.append(FloatText(self.girl.x, self.girl.y - 34, "MY HERO!", (255, 150, 190), 1.6))
            if self.t >= self.MOUNT_T:
                self.mounted = True
                self.app.audio.play("neigh", 0.7)
                for _ in range(12):
                    self.particles.append(Particle(290 + random.uniform(-14, 14), 204, random.uniform(-20, 20),
                                                   random.uniform(-16, -4), random.uniform(0.5, 1.0),
                                                   (220, 190, 150), size=2, kind="smoke", drag=1.5))
        if 0 < self.hearts and not self.mounted and random.random() < dt * 5:
            hx = (self.hero.x + self.girl.x) / 2 + random.uniform(-6, 6)
            self.particles.append(Particle(hx, self.girl.y - 28, random.uniform(-6, 6), -18, 1.4, (240, 70, 110),
                                           kind="img", img=HEART))
        self.particles = [pt for pt in self.particles if pt.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        for x, y, _, img in self.clouds:
            surf.blit(img, (int(x) - 60, int(y)))
        L = self.layer
        L.fill((0, 0, 0, 0))
        if self.mounted:
            x, y, k, p = self._ride_pos()
            if p < 1:
                img = self.ride[0] if p <= 0 else self.ride[1 + int(self.t * 8) % 2]
                w, h = max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))
                img = pygame.transform.scale(img, (w, h))
                sw = int(30 * k)
                pygame.draw.ellipse(L, (0, 0, 0, 70), (int(x) - sw // 2, int(y) - 2, sw, max(2, int(5 * k))))
                L.blit(img, img.get_rect(midbottom=(int(x) + 1, int(y) + 1)))
        else:
            self.girl.draw(L)
            self.hero.draw(L)
        for pt in self.particles:
            pt.draw(L)
        L.fill(self.theme["tint"], special_flags=pygame.BLEND_RGB_MULT)
        surf.blit(L, (0, 0))
        for t in self.texts:
            t.draw(surf)

        # credits scroll up, then the last lines stay put
        gap = 13
        stop = 150 - (len(self.lines) - 1) * gap
        y0 = max(stop, H - (self.t - 1.0) * 12)
        cx = 112                                   # credits column, clear of the riders
        for i, (line, size) in enumerate(self.lines):
            y = int(y0 + i * gap)
            if 26 < y < H - 8 and line:
                credit = size > 13
                col = GOLD if (credit or "RELOADED" in line) else CREAM
                gfx.text(surf, line, 16 if credit else size, (cx, y), col, outline=True, smooth=credit)
        img = gfx.fancy_text("THE END", 30, (255, 236, 130), (232, 104, 30))
        surf.blit(img, img.get_rect(center=(W // 2, 14 + max(0, 20 - int(self.t * 10)))))


def _heart():
    s = pygame.Surface((7, 6), pygame.SRCALPHA)
    for y, row in enumerate((".##.##.", "#######", "#######", ".#####.", "..###..", "...#...")):
        for x, ch in enumerate(row):
            if ch == "#":
                s.set_at((x, y), (236, 60, 100))
    s.set_at((1, 1), (255, 200, 210))
    return s


HEART = _heart()
