"""Title, play, game-over and victory scenes."""
import math
import random

import pygame

import gfx
from config import (W, H, OY, PLAY_H, LIVES, STAGES, SCROLL_SPEED, MAX_BOMBS, WEAPON_TIME, BOUNTY_EXTRA_LIFE,
                    INVULN_RESPAWN, HEROES, HERO_ORDER)
from entities import (Player, Enemy, Boss, Bullet, Dynamite, Explosion, Puff, Item, Barrel, ENEMY_STATS)

GOLD = (255, 214, 90)
WHITE = (250, 246, 236)
RED = (255, 96, 90)


class Run:
    """State carried from stage to stage."""

    def __init__(self, hero="hank"):
        self.hero = hero
        self.score = 0
        self.lives = LIVES
        self.player = Player(hero)
        self.next_life = BOUNTY_EXTRA_LIFE


def _build_events(idx, length, rng):
    s = STAGES[idx]
    dens = s["density"]
    events = []
    d = 120.0
    while d < length - 80:
        r = rng.random()
        if r < 0.34:
            n = rng.randint(2, min(4, 3 + idx // 2))
            x0 = rng.randint(80, W - 80 - 40 * n)
            for i in range(n):
                events.append((d + i * 12, "outlaw", x0 + i * 40))
        elif r < 0.6:
            events.append((d, "gunman", rng.randint(70, W - 70)))
        elif r < 0.76 and idx >= 1:
            events.append((d, "dynamite", rng.randint(70, W - 70)))
        elif r < 0.9 and idx >= 1:
            for i in range(1 + idx // 3):
                events.append((d + i * 18, "rider", rng.randint(60, W - 60)))
        else:
            events.append((d, "gunman", rng.randint(70, 140)))
            events.append((d + 10, "gunman", rng.randint(180, W - 70)))
        d += rng.uniform(80, 130) / dens
    events.sort()
    return events


class TitleScene:
    def __init__(self, app):
        self.app = app
        self.stage = gfx.Stage(0, 400, 5)
        self.t = 0.0

    def update(self, dt, inp):
        self.t += dt
        if inp.confirm:
            self.app.audio.play("start")
            self.app.change(CharacterSelectScene(self.app))
        elif inp.pause or inp.quit:
            self.app.running = False

    def draw(self, s):
        sp = self.app.sprites
        cam = int(400 - (self.t * 30) % 400)
        s.blit(self.stage.surf, (0, OY), (0, cam, W, PLAY_H))
        pygame.draw.rect(s, (14, 8, 20), (0, 0, W, OY))
        veil = pygame.Surface((W, 196), pygame.SRCALPHA)
        veil.fill((20, 10, 8, 175))
        s.blit(veil, (0, 50))
        for i, ch in enumerate("OUTLAW GULCH"):
            y = 80 + math.sin(self.t * 3 + i * 0.5) * 3
            col = gfx.lerp((255, 220, 90), (255, 130, 70), (math.sin(self.t * 2 + i * 0.4) + 1) / 2)
            gfx.text(s, ch, 44, (W // 2 - 12 * 11 + i * 23 + 11, y), col)
        gfx.text(s, "BOUNTY HUNTER SHOOT-'EM-UP", 16, (W // 2, 112), WHITE)
        if int(self.t * 2) % 2 == 0:
            gfx.text(s, "PRESS SPACE TO START", 22, (W // 2, 138), GOLD)
        gfx.text(s, "HI-SCORE $%06d" % self.app.save["hi"], 16, (W // 2, 30), GOLD)
        lines = ["WASD / ARROWS  move", "K or SPACE shoot ahead   J / L shoot diagonally",
                 "Hold left mouse button to aim with the mouse", "B or right mouse: dynamite bomb     ESC: pause"]
        for i, ln in enumerate(lines):
            gfx.text(s, ln, 14, (W // 2, 188 + i * 12), (225, 215, 235))
        x = (self.t * 40) % (W + 60) - 30
        s.blit(sp.hero["hank"][(0, int(self.t * 8) % 2)], (x - 9, 218))
        s.blit(sp.enemy["outlaw"][int(self.t * 8) % 2], (W - x - 9, 236))


class CharacterSelectScene:
    """Pick the hero before the game starts."""

    CARD_W, CARD_H = 140, 196

    def __init__(self, app):
        self.app = app
        self.stage = gfx.Stage(0, 400, 5)
        self.sel = 0
        self.t = 0.0
        self.prev_dx = 0

    def card_rect(self, i):
        return pygame.Rect(14 + i * (self.CARD_W + 12), 40, self.CARD_W, self.CARD_H)

    def update(self, dt, inp):
        self.t += dt
        if inp.dx and inp.dx != self.prev_dx:
            self.sel = (self.sel + inp.dx) % len(HERO_ORDER)
            self.app.audio.play("tick")
        self.prev_dx = inp.dx
        if inp.mouse_active:
            for i in range(len(HERO_ORDER)):
                if self.card_rect(i).collidepoint(inp.mouse_pos):
                    self.sel = i
        if inp.confirm:
            self.app.audio.play("start")
            self.app.change(PlayScene(self.app, 0, Run(HERO_ORDER[self.sel])))
        elif inp.pause or inp.quit:
            self.app.change(TitleScene(self.app))

    def draw(self, s):
        sp = self.app.sprites
        cam = int(400 - (self.t * 20) % 400)
        s.blit(self.stage.surf, (0, OY), (0, cam, W, PLAY_H))
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((14, 8, 22, 205))
        s.blit(veil, (0, 0))
        gfx.text(s, "CHOOSE YOUR HERO", 28, (W // 2, 22), GOLD)
        labels = ("SPEED", "FIRE RATE", "HEALTH", "BOMBS")
        for i, key in enumerate(HERO_ORDER):
            hero = HEROES[key]
            r = self.card_rect(i)
            chosen = i == self.sel
            pygame.draw.rect(s, (40, 26, 44) if chosen else (24, 16, 32), r)
            pygame.draw.rect(s, GOLD if chosen else (80, 60, 90), r, 2 if chosen else 1)
            port = sp.portrait[key]
            bob = int(math.sin(self.t * 4) * 2) if chosen else 0
            pygame.draw.ellipse(s, (0, 0, 0), (r.centerx - 24, r.y + 120, 48, 10))
            s.blit(port, (r.centerx - port.get_width() // 2, r.y + 124 - port.get_height() - bob + 4))
            gfx.text(s, hero["name"], 16, (r.centerx, r.y + 22), WHITE if chosen else (170, 160, 180))
            for j, (lab, pips) in enumerate(zip(labels, hero["pips"])):
                y = r.y + 142 + j * 12
                gfx.text(s, lab, 12, (r.x + 8, y), (200, 190, 210), anchor="midleft", shadow=False)
                for k in range(5):
                    c = (GOLD if chosen else (190, 160, 90)) if k < pips else (60, 46, 70)
                    pygame.draw.rect(s, c, (r.right - 8 - (5 - k) * 9, y - 3, 7, 6))
        hero = HEROES[HERO_ORDER[self.sel]]
        gfx.text(s, hero["tag"], 14, (W // 2, H - 12), (225, 215, 235))
        gfx.text(s, "A/D or arrows: choose     SPACE: start     ESC: back", 12, (W // 2, 33), (160, 150, 180))


class PlayScene:
    def __init__(self, app, idx, run):
        self.app = app
        self.idx = idx
        self.run = run
        self.cfg = STAGES[idx]
        self.rng = random.Random(idx * 31 + 7)
        self.stage = gfx.Stage(self.cfg["theme"], self.cfg["length"], 100 + idx)
        self.player = run.player
        boots, hp = self.player.boots, self.player.hp
        self.player.reset(full=False)
        self.player.boots, self.player.hp = boots, max(hp, self.player.hp)
        self.player.x, self.player.y = W / 2, H - 40
        self.player.invuln = 1.0
        self.length = self.cfg["length"]
        self.cam = float(self.length)
        self.dist = 0.0
        self.events = _build_events(idx, self.length, self.rng)
        self.enemies, self.bullets, self.ebullets = [], [], []
        self.dynamites, self.explosions, self.puffs = [], [], []
        self.items = []
        self.barrels = [Barrel(x, y) for x, y in self.stage.barrels]
        self.boss = None
        self.phase = "intro"
        self.t = 0.0
        self.paused = False
        self.clock = 0.0
        self.dt = 1 / 60
        self.shake = 0.0
        self.bomb_flash = 0.0
        self.respawn_t = 0.0
        self.sound_t = 0.0
        self.tally = None

    # ------------------------------------------------------------ services for entities
    def sy(self, wy):
        return wy - self.cam + OY

    def aim_at(self, x, y, p, spread=0.0):
        return math.atan2(p.y - 9 - y, p.x - x) + self.rng.uniform(-spread, spread)

    def enemy_shot(self, x, y, ang, speed):
        self.ebullets.append(Bullet(x, y, math.cos(ang) * speed, math.sin(ang) * speed, 1, False, 7.0, False, 3))
        self.puffs.append(Puff(x, y, self.rng.uniform(-8, 8), self.rng.uniform(-6, 6), 0.35, 2))
        if self.sound_t <= 0:
            self.app.audio.play("enemy_shot")
            self.sound_t = 0.08

    def throw_dynamite(self, x, y, tx, ty):
        self.dynamites.append(Dynamite(x, y, tx, ty))

    def spawn_enemy(self, kind, x, y):
        self.enemies.append(Enemy(kind, x, y, self))

    # -------------------------------------------------------------------- helpers
    def blockers(self):
        out = []
        top, bot = self.cam - 24, self.cam + PLAY_H + 24
        for o in self.stage.obstacles:
            if o.bottom >= top and o.top <= bot:
                out.append(o.move(0, OY - self.cam))
        for b in self.barrels:
            if top <= b.wy <= bot:
                out.append(b.rect().move(0, OY - self.cam))
        return out

    def add_score(self, pts):
        self.run.score += pts
        if self.run.score >= self.run.next_life:
            self.run.next_life += BOUNTY_EXTRA_LIFE
            self.run.lives += 1
            self.app.audio.play("life")

    def burst(self, x, y, n=8, color=(200, 150, 100), speed=40, life=0.5, size=3):
        for _ in range(n):
            a = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(0.3, 1.0) * speed
            self.puffs.append(Puff(x, y, math.cos(a) * v, math.sin(a) * v, life * self.rng.uniform(0.6, 1.2), size, color))

    def drop(self, x, y, force=None):
        if force is None:
            if self.rng.random() > 0.17:
                return
            kinds = ["cash"] * 7 + ["heart"] * 3 + ["boots"] * 2 + ["shotgun"] * 3 + ["rifle"] * 2 + ["bomb"] * 3
            force = self.rng.choice(kinds)
        self.items.append(Item(force, x - 7, y - OY + self.cam - 7))

    def kill_enemy(self, e):
        e.dead = True
        self.add_score(e.score)
        self.burst(e.x, e.cy, 9, (190, 60, 50) if e.kind != "rider" else (170, 120, 80), 55, 0.55, 3)
        self.app.audio.play("kill")
        self.drop(e.x, e.cy)

    # ------------------------------------------------------------------- update
    def update(self, dt, inp):
        self.dt = dt
        if inp.pause and self.phase in ("run", "boss"):
            self.paused = not self.paused
        if self.paused:
            if inp.quit:
                self.finish()
                self.app.change(TitleScene(self.app))
            return
        self.clock += dt
        self.sound_t = max(0.0, self.sound_t - dt)
        self.shake = max(0.0, self.shake - dt)
        self.bomb_flash = max(0.0, self.bomb_flash - dt)
        getattr(self, "_" + self.phase)(dt, inp)

    def _intro(self, dt, inp):
        self.t += dt
        if self.t > 2.4 or (inp.confirm and self.t > 0.6):
            self.phase, self.t = "run", 0.0

    def _run(self, dt, inp):
        self.dist = min(self.length, self.dist + SCROLL_SPEED * dt)
        self.cam = self.length - self.dist
        while self.events and self.events[0][0] <= self.dist and len(self.enemies) < 14:
            _, kind, x = self.events.pop(0)
            self.spawn_enemy(kind, x, OY - 12)
        self._combat(dt, inp)
        if self.dist >= self.length and not self.player.dead:
            self.phase, self.t = "poster", 0.0
            self.app.audio.play("boss")

    def _poster(self, dt, inp):
        self.t += dt
        if self.t > 3.8 or (inp.confirm and self.t > 1.2):
            self.boss = Boss(self.cfg["kind"], self.cfg["hp"], self)
            self.ebullets.clear()
            self.phase, self.t = "boss", 0.0

    def _boss(self, dt, inp):
        self._combat(dt, inp)
        if self.boss and self.boss.dying > 2.4:
            self.boss = None
            for dx, k in ((-22, "cash"), (0, "heart"), (22, "bomb")):
                self.drop(W / 2 + dx, OY + 70, k)
            for _ in range(6):
                self.drop(self.rng.randint(60, W - 60), self.rng.randint(OY + 40, OY + 130), "cash")
            self.phase, self.t = "clear", 0.0
            self.app.audio.play("clear")
            self.ebullets.clear()
            self.dynamites.clear()
            self.tally = dict(hp=self.player.hp * 500, bombs=self.player.bombs * 300)
            self.add_score(self.cfg["reward"])

    def _clear(self, dt, inp):
        self.t += dt
        self.player.invuln = max(self.player.invuln, 1.0)
        self._combat(dt, inp)
        if self.t > 1.5 and self.tally:
            self.add_score(self.tally["hp"] + self.tally["bombs"])
            self.tally = dict(done=True, hp=self.tally["hp"], bombs=self.tally["bombs"])
        if self.t > 5.0 or (inp.confirm and self.t > 2.5):
            self.finish()
            if self.idx + 1 >= len(STAGES):
                self.app.change(WinScene(self.app, self.run.score, self.run.hero))
            else:
                self.app.change(PlayScene(self.app, self.idx + 1, self.run))

    def _dead(self, dt, inp):
        self.t += dt
        self._combat(dt, inp, shooting=False, moving=False)
        if self.t > 1.8:
            self.run.lives -= 1
            if self.run.lives <= 0:
                self.finish()
                self.app.change(GameOverScene(self.app, self.run.score, self.idx + 1))
                return
            p = self.player
            p.reset(full=False)
            p.invuln = INVULN_RESPAWN
            self.ebullets.clear()
            self.dynamites.clear()
            self.explosions.clear()
            self.phase = "boss" if self.boss else "run"
            self.t = 0.0

    def finish(self):
        self.app.record_score(self.run.score)

    # ----------------------------------------------------------------- combat core
    def _combat(self, dt, inp, shooting=True, moving=True):
        p = self.player
        a = self.app.audio
        if moving:
            p.update(dt, inp, self.blockers())
        elif not p.dead:
            p.invuln = max(0.0, p.invuln - dt)

        if shooting and not p.dead:
            new, snd = p.shoot(inp)
            if new:
                self.bullets.extend(new)
                a.play(snd)
                self.puffs.append(Puff(p.x + p.aim, p.y - 14, self.rng.uniform(-6, 6), -self.rng.uniform(14, 30), 0.55, 3))
            if inp.bomb and p.bombs > 0:
                self.use_bomb()

        for e in self.enemies:
            e.update(dt, self)
        if self.boss:
            self.boss.update(dt, self)
        for b in self.bullets:
            b.update(dt)
        for b in self.ebullets:
            b.update(dt)
        for d in self.dynamites[:]:
            if d.update(dt):
                self.dynamites.remove(d)
                self.explosions.append(Explosion(d.tx, d.ty, 30))
                a.play("boom")
        for ex in self.explosions:
            ex.t += dt
        self.puffs = [q for q in self.puffs if q.update(dt)]
        for it in self.items:
            it.t += dt
        for br in self.barrels:
            br.flash = max(0.0, br.flash - dt)

        self._collisions()

        self.bullets = [b for b in self.bullets if b.alive()]
        self.ebullets = [b for b in self.ebullets if b.alive()]
        self.enemies = [e for e in self.enemies if not e.dead]
        self.explosions = [x for x in self.explosions if x.t < x.life]
        self.barrels = [b for b in self.barrels if b.hp > 0 and b.wy < self.cam + PLAY_H + 40]
        self.items = [i for i in self.items if i.wy < self.cam + PLAY_H + 40]

        if p.dead and self.phase in ("run", "boss"):
            self.phase, self.t = "dead", 0.0
            a.play("die")
            self.burst(p.x, p.y - 8, 14, (230, 220, 200), 60, 0.8, 3)

    def use_bomb(self):
        p = self.player
        p.bombs -= 1
        self.app.audio.play("bomb")
        self.bomb_flash = 0.5
        self.shake = 0.5
        self.ebullets.clear()
        self.dynamites.clear()
        self.explosions.append(Explosion(W / 2, OY + PLAY_H / 2, 170, 0, 0, False))
        for e in self.enemies:
            e.hp -= 4
            e.flash = 0.2
            if e.hp <= 0 and not e.dead:
                self.kill_enemy(e)
        if self.boss and self.boss.state != "enter" and self.boss.dying == 0:
            self.hit_boss(14)

    def hit_boss(self, dmg):
        b = self.boss
        if b.state == "enter" or b.dying > 0:
            return
        b.hp -= dmg
        b.flash = 0.08
        if b.hp <= 0:
            b.dying = 0.001
            self.add_score(1000)
            self.ebullets.clear()
            self.dynamites.clear()
            for e in self.enemies:
                if not e.dead:
                    self.kill_enemy(e)
            self.app.audio.play("bomb")
            self.shake = 1.4

    def _collisions(self):
        p = self.player
        a = self.app.audio
        top = OY
        # player shots
        for b in self.bullets:
            for e in self.enemies:
                if e.dead or id(e) in b.hit:
                    continue
                if math.hypot(b.x - e.x, b.y - e.cy) < e.radius + b.r:
                    e.hp -= b.dmg
                    e.flash = 0.08
                    a.play("hit")
                    self.burst(b.x, b.y, 2, (255, 230, 150), 30, 0.2, 2)
                    if e.hp <= 0:
                        self.kill_enemy(e)
                    b.hit.add(id(e))
                    if not b.pierce:
                        b.life = 0
                        break
            if b.life <= 0:
                continue
            boss = self.boss
            if boss and boss.state != "enter" and boss.dying == 0 and math.hypot(b.x - boss.x, b.y - boss.cy) < boss.radius + b.r:
                self.hit_boss(b.dmg)
                a.play("hit")
                self.burst(b.x, b.y, 2, (255, 230, 150), 30, 0.2, 2)
                if not b.pierce:
                    b.life = 0
                    continue
            for br in self.barrels:
                if br.hp > 0 and id(br) not in b.hit and br.rect().move(0, OY - self.cam).inflate(2, 2).collidepoint(b.x, b.y):
                    br.hp -= b.dmg
                    br.flash = 0.08
                    b.hit.add(id(br))
                    a.play("hit")
                    if br.hp <= 0:
                        self.burst(br.x + 7, self.sy(br.wy) + 7, 8, (170, 110, 60), 50, 0.5, 3)
                        self.add_score(50)
                        self.items.append(Item(self.rng.choice(["cash", "heart", "boots", "shotgun", "rifle", "bomb", "bomb"]),
                                               br.x, br.wy))
                    if not b.pierce:
                        b.life = 0
                        break

        if p.dead:
            return
        hit = False
        for b in self.ebullets:
            if math.hypot(b.x - p.x, b.y - (p.y - 8)) < 5 + b.r:
                b.life = 0
                hit = True
        for e in self.enemies:
            if e.contact and not e.dead and math.hypot(e.x - p.x, e.cy - (p.y - 8)) < e.radius + 5:
                hit = True
        boss = self.boss
        if boss and boss.state != "enter" and boss.dying == 0 and math.hypot(boss.x - p.x, boss.cy - (p.y - 8)) < boss.radius + 6:
            hit = True
        for ex in self.explosions:
            if not ex.applied:
                ex.applied = True
                if ex.harms_enemies:
                    for e in self.enemies:
                        if not e.dead and math.hypot(e.x - ex.x, e.cy - ex.y) < ex.radius + 4:
                            e.hp -= ex.dmg_enemy
                            e.flash = 0.1
                            if e.hp <= 0:
                                self.kill_enemy(e)
                    self.burst(ex.x, ex.y, 10, (255, 170, 60), 70, 0.6, 3)
                    self.shake = max(self.shake, 0.25)
                if ex.dmg_player and math.hypot(ex.x - p.x, ex.y - (p.y - 8)) < ex.radius + 4:
                    hit = True
        if hit and p.hurt():
            a.play("hurt")
            self.shake = 0.3
            self.burst(p.x, p.y - 8, 6, (230, 60, 60), 40, 0.4, 2)

        # pickups
        for it in self.items[:]:
            if math.hypot(it.x + 7 - p.x, self.sy(it.wy) + 7 - (p.y - 8)) < 13:
                self.items.remove(it)
                self.pick_up(it.kind)

    def pick_up(self, kind):
        p = self.player
        self.app.audio.play("pickup")
        if kind == "heart":
            p.hp = min(p.max_hp, p.hp + 1)
        elif kind == "boots":
            p.boots = True
        elif kind in ("shotgun", "rifle"):
            p.weapon, p.wtime = kind, WEAPON_TIME
        elif kind == "bomb":
            if p.bombs < MAX_BOMBS:
                p.bombs += 1
            else:
                self.add_score(300)
        else:
            self.add_score(500)

    # --------------------------------------------------------------------- draw
    def draw(self, s):
        sp = self.app.sprites
        ox = oy = 0
        if self.shake > 0:
            ox, oy = self.rng.randint(-2, 2), self.rng.randint(-2, 2)
        view = pygame.Surface((W, H))
        view.fill((10, 6, 16))
        view.blit(self.stage.surf, (0, OY), (0, int(self.cam), W, PLAY_H))
        shadow = pygame.Surface((16, 7), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 70), (0, 0, 16, 7))

        for br in self.barrels:
            img = sp.barrel if br.flash <= 0 else sp.flashed(sp.barrel)
            view.blit(img, (br.x - 1, self.sy(br.wy) - 1))
        for it in self.items:
            bob = math.sin(it.t * 5) * 2
            view.blit(sp.items[it.kind], (it.x - 1, self.sy(it.wy) - 1 + bob))
        for d in self.dynamites:
            if (int(d.t * 8) % 2) == 0:
                pygame.draw.circle(view, (255, 90, 60), (int(d.tx), int(d.ty)), 30, 1)
            pygame.draw.circle(view, (255, 120, 80), (int(d.tx), int(d.ty)), int(30 * min(1, d.t / d.flight)), 1)
        ents = [("e", e, e.y) for e in self.enemies]
        if self.boss:
            ents.append(("b", self.boss, self.boss.y + 25))
        ents.append(("p", self.player, self.player.y))
        for kind, o, y in sorted(ents, key=lambda t: t[2]):
            if kind == "e":
                if o.kind == "rider":
                    img = sp.rider[int(o.anim * 1.4) % 2]
                    off = (11, 28)
                else:
                    img = sp.enemy[o.kind][int(o.anim) % 2]
                    off = (9, 21)
                view.blit(shadow, (o.x - 8, o.y - 4))
                view.blit(sp.flashed(img) if o.flash > 0 else img, (o.x - off[0], o.y - off[1]))
            elif kind == "b":
                img = sp.boss[o.kind][int(o.anim) % 2]
                if o.dying:
                    if int(o.dying * 20) % 2 == 0:
                        img = sp.flashed(img)
                    if self.rng.random() < 0.5:
                        self.burst(o.x + self.rng.uniform(-18, 18), o.y + self.rng.uniform(-22, 22), 3,
                                   self.rng.choice(((255, 200, 80), (255, 120, 50), (240, 240, 240))), 60, 0.5, 4)
                elif o.flash > 0:
                    img = sp.flashed(img)
                view.blit(pygame.transform.scale(shadow, (30, 12)), (o.x - 15, o.y + 20))
                view.blit(img, (o.x - img.get_width() / 2, o.y - img.get_height() / 2 - 2))
            else:
                if o.dead:
                    continue
                if o.invuln > 0 and int(o.invuln * 16) % 2 == 0:
                    continue
                view.blit(shadow, (o.x - 8, o.y - 4))
                view.blit(sp.hero[o.hero][(o.aim, int(o.anim) % 2)], (o.x - 9, o.y - 21))
        for q in self.puffs:
            t = q.age / q.life
            r = max(1, int(q.size * (0.6 + t * 1.6)))
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, q.color + (int(190 * (1 - t)),), (r, r), r)
            view.blit(surf, (q.x - r, q.y - r))
        for b in self.bullets:
            pygame.draw.circle(view, (255, 244, 170), (int(b.x), int(b.y)), 2)
            pygame.draw.circle(view, (255, 190, 60), (int(b.x - b.vx * 0.012), int(b.y - b.vy * 0.012)), 1)
        for b in self.ebullets:
            pygame.draw.circle(view, (40, 14, 20), (int(b.x), int(b.y)), 4)
            pygame.draw.circle(view, (255, 120, 60), (int(b.x), int(b.y)), 3)
            pygame.draw.circle(view, (255, 230, 150), (int(b.x), int(b.y)), 1)
        for d in self.dynamites:
            view.blit(sp.dynamite, (d.x - 4, d.y - 7 - d.height))
        for ex in self.explosions:
            k = ex.t / ex.life
            r = int(ex.radius * (0.35 + 0.65 * math.sqrt(k)))
            surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            for col, f in (((255, 120, 40), 1.0), ((255, 190, 70), 0.72), ((255, 250, 210), 0.4)):
                pygame.draw.circle(surf, col + (int(220 * (1 - k)),), (r + 1, r + 1), max(1, int(r * f)))
            view.blit(surf, (ex.x - r - 1, ex.y - r - 1))
        if self.bomb_flash > 0:
            fl = pygame.Surface((W, PLAY_H), pygame.SRCALPHA)
            fl.fill((255, 240, 200, int(200 * self.bomb_flash / 0.5)))
            view.blit(fl, (0, OY))

        self.draw_hud(view)
        self.draw_overlay(view)
        s.fill((0, 0, 0))
        s.blit(view, (ox, oy))

    def draw_hud(self, s):
        p = self.player
        sp = self.app.sprites
        pygame.draw.rect(s, (16, 10, 24), (0, 0, W, OY))
        pygame.draw.line(s, (90, 60, 100), (0, OY - 1), (W, OY - 1))
        gfx.text(s, "$%06d" % self.run.score, 16, (4, 8), GOLD, anchor="midleft")
        for i in range(p.max_hp):
            s.blit(sp.heart_full if i < p.hp else sp.heart_empty, (70 + i * 11, 3))
        gfx.text(s, "x%d" % max(0, self.run.lives), 16, (142, 8), WHITE, anchor="midleft")
        s.blit(sp.items["bomb"], (160, 1))
        gfx.text(s, "x%d" % p.bombs, 16, (178, 8), WHITE, anchor="midleft")
        if p.weapon != "revolver":
            gfx.text(s, "%s %ds" % (p.weapon.upper(), int(p.wtime) + 1), 14, (206, 8), (150, 230, 255), anchor="midleft")
        if p.boots:
            gfx.text(s, "BOOTS", 14, (W - 4, 8), (255, 220, 150), anchor="midright")
        boss = self.boss
        if boss and boss.state != "enter":
            w = 200
            x = (W - w) // 2
            pygame.draw.rect(s, (30, 10, 20), (x - 2, OY + 3, w + 4, 10))
            pygame.draw.rect(s, (200, 40, 50), (x, OY + 5, int(w * max(0, boss.hp) / boss.max_hp), 6))
            gfx.text(s, self.cfg["boss"], 12, (W // 2, OY + 9), WHITE, shadow=True)

    def draw_overlay(self, s):
        cx = W // 2
        if self.phase == "intro":
            veil = pygame.Surface((W, 80), pygame.SRCALPHA)
            veil.fill((10, 6, 20, 200))
            s.blit(veil, (0, 100))
            gfx.text(s, "STAGE %d" % (self.idx + 1), 34, (cx, 124), GOLD)
            gfx.text(s, self.cfg["name"], 24, (cx, 156), WHITE)
        elif self.phase == "poster":
            self.draw_poster(s)
        elif self.phase == "dead" and self.run.lives <= 1 and self.t > 0.8:
            gfx.text(s, "GAME OVER", 32, (cx, 128), RED)
        elif self.phase == "clear":
            veil = pygame.Surface((W, 92), pygame.SRCALPHA)
            veil.fill((10, 6, 20, 200))
            s.blit(veil, (0, 92))
            gfx.text(s, "BOUNTY COLLECTED!", 28, (cx, 112), GOLD)
            gfx.text(s, "%s  $%d" % (self.cfg["boss"], self.cfg["reward"]), 16, (cx, 136), WHITE)
            if self.tally and self.t > 1.5:
                gfx.text(s, "HEALTH BONUS $%d   BOMB BONUS $%d" % (self.tally["hp"], self.tally["bombs"]), 14,
                         (cx, 158), (150, 230, 150))
        if self.paused:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((10, 6, 20, 170))
            s.blit(veil, (0, 0))
            gfx.text(s, "PAUSED", 34, (cx, 112), GOLD)
            gfx.text(s, "ESC: resume     Q: quit to title", 16, (cx, 146), WHITE)

    def draw_poster(self, s):
        sp = self.app.sprites
        k = min(1.0, self.t / 0.35)
        w, h = 190, 212
        x, y = (W - w) // 2, OY + 14 - int((1 - k) * 260)
        pygame.draw.rect(s, (60, 40, 30), (x - 3, y - 3, w + 6, h + 6))
        pygame.draw.rect(s, (222, 196, 140), (x, y, w, h))
        pygame.draw.rect(s, (170, 138, 88), (x + 4, y + 4, w - 8, h - 8), 2)
        for i in range(6):
            pygame.draw.circle(s, (170, 138, 88), (x + 10 + i * 34, y + h - 8), 2)
        gfx.text(s, "WANTED", 40, (x + w // 2, y + 28), (120, 30, 24), shadow=False)
        gfx.text(s, "DEAD OR ALIVE", 14, (x + w // 2, y + 52), (96, 60, 40), shadow=False)
        img = sp.boss[self.cfg["kind"]][0]
        big = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
        pygame.draw.rect(s, (200, 176, 124), (x + 40, y + 62, w - 80, 100))
        pygame.draw.rect(s, (96, 60, 40), (x + 40, y + 62, w - 80, 100), 2)
        s.blit(big, (x + w // 2 - big.get_width() // 2, y + 62 + (100 - big.get_height()) // 2 + 6))
        gfx.text(s, self.cfg["boss"], 22, (x + w // 2, y + 178), (70, 30, 24), shadow=False)
        gfx.text(s, "REWARD  $%d" % self.cfg["reward"], 18, (x + w // 2, y + 198), (50, 90, 40), shadow=False)


class _EndScene:
    def __init__(self, app, score):
        self.app = app
        self.score = score
        self.stage = gfx.Stage(0, 300, 9)
        self.t = 0.0

    def update(self, dt, inp):
        self.t += dt
        if self.t > 0.8 and (inp.confirm or inp.pause):
            self.app.change(TitleScene(self.app))

    def panel(self, s):
        s.blit(self.stage.surf, (0, OY), (0, 300 - int((self.t * 20) % 300), W, PLAY_H))
        veil = pygame.Surface((W, 160), pygame.SRCALPHA)
        veil.fill((12, 6, 20, 200))
        s.blit(veil, (0, 60))
        pygame.draw.rect(s, (16, 10, 24), (0, 0, W, OY))


class GameOverScene(_EndScene):
    def __init__(self, app, score, stage_no):
        super().__init__(app, score)
        self.stage_no = stage_no

    def draw(self, s):
        self.panel(s)
        gfx.text(s, "GAME OVER", 46, (W // 2, 94), RED)
        gfx.text(s, "You made it to stage %d" % self.stage_no, 18, (W // 2, 128), WHITE)
        gfx.text(s, "BOUNTY $%06d" % self.score, 26, (W // 2, 156), GOLD)
        if self.score >= self.app.save["hi"] and self.score > 0:
            gfx.text(s, "NEW HI-SCORE!", 18, (W // 2, 180), (120, 255, 140))
        if int(self.t * 2) % 2 == 0:
            gfx.text(s, "PRESS SPACE", 16, (W // 2, 204), (200, 200, 235))


class WinScene(_EndScene):
    def __init__(self, app, score, hero="hank"):
        super().__init__(app, score)
        self.hero = hero

    def draw(self, s):
        self.panel(s)
        gfx.text(s, "THE GULCH IS FREE!", 34, (W // 2, 94), GOLD)
        gfx.text(s, "All five outlaw bosses brought to justice.", 16, (W // 2, 126), WHITE)
        gfx.text(s, "TOTAL BOUNTY $%06d" % self.score, 26, (W // 2, 156), GOLD)
        if int(self.t * 2) % 2 == 0:
            gfx.text(s, "PRESS SPACE", 16, (W // 2, 204), (200, 200, 235))
        sp = self.app.sprites
        s.blit(sp.hero[self.hero][(0, int(self.t * 6) % 2)], (W // 2 - 9, 224 - abs(math.sin(self.t * 5)) * 10))
