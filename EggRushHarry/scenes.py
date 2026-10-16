"""Title, play, game-over and victory scenes."""
import math
import random

import pygame

import gfx
from config import (W, H, OY, TILE, LIVES, NUM_LEVELS, BIRD_FREE_FROM, CAGE_RECT, CAGE_CENTER, GROUND_ROW,
                    SCORE_EGG, SCORE_GRAIN, SCORE_TIME, SCORE_CLEAR, EXTRA_LIFE_EVERY,
                    level_time, hen_speed)
from entities import Player, Hen, Bird
from levels import Level

GOLD = (255, 214, 80)
WHITE = (250, 250, 245)
RED = (255, 96, 96)


def draw_ground_sprites(scene, surf, t):
    """Harry runs along the ground chased by a hen (title / end screens)."""
    sp = scene.app.sprites
    gy = OY + GROUND_ROW * TILE
    x = (t * 50) % (W + 80) - 40
    surf.blit(sp.harry["walk%d" % (int(t * 8) % 2)], (x - 8, gy - 23))
    hx = x - 46
    surf.blit(sp.hen["w%d" % (int(t * 8) % 2)], (hx - 9, gy - 17))


class TitleScene:
    def __init__(self, app):
        self.app = app
        self.level = Level(1)
        self.bg = gfx.render_level(self.level)
        self.t = 0.0

    def update(self, dt, inp):
        self.t += dt
        if inp.jump_pressed:
            self.app.audio.play("start")
            self.app.change(PlayScene(self.app, 1, 0, LIVES))
        elif inp.pause_pressed or inp.quit_pressed:
            self.app.running = False

    def draw(self, s):
        s.blit(self.bg, (0, 0))
        sp = self.app.sprites
        veil = pygame.Surface((W, 150), pygame.SRCALPHA)
        veil.fill((10, 6, 24, 150))
        s.blit(veil, (0, 56))
        title = "EGG RUSH HARRY"
        x0 = W // 2 - len(title) * 11
        for i, ch in enumerate(title):
            y = 86 + math.sin(self.t * 3 + i * 0.5) * 4
            col = gfx.lerp((255, 220, 90), (255, 120, 80), (math.sin(self.t * 2 + i * 0.4) + 1) / 2)
            gfx.text(s, ch, 44, (x0 + i * 22 + 11, y), col)
        gfx.text(s, "Collect every egg. Dodge the hens. Beware the big bird!", 16, (W // 2, 122), WHITE)
        if int(self.t * 2) % 2 == 0:
            gfx.text(s, "PRESS SPACE TO START", 22, (W // 2, 158), GOLD)
        gfx.text(s, "ARROWS / WASD: move and climb     SPACE: jump", 14, (W // 2, 186), (200, 200, 230))
        gfx.text(s, "ESC: pause     Q: quit to title", 14, (W // 2, 198), (200, 200, 230))
        gfx.text(s, "HI-SCORE %06d" % self.app.save["hi"], 18, (W // 2, 32), GOLD)
        s.blit(sp.cage_open, CAGE_RECT[:2])
        s.blit(sp.bird_small, (CAGE_CENTER[0] - 15, CAGE_CENTER[1] - 12 + math.sin(self.t * 6) * 2))
        draw_ground_sprites(self, s, self.t)


class PlayScene:
    def __init__(self, app, n, score, lives):
        self.app = app
        self.n = n
        self.score = score
        self.lives = lives
        self.rng = random.Random(n * 977 + 13)
        self.level = Level(n)
        self.bg = gfx.render_level(self.level)
        self.player = Player(self.level)
        speed = hen_speed(n)
        self.hens = [Hen(x, y, speed, self.rng) for x, y in self.level.hen_spawns]
        self.free_bird = n >= BIRD_FREE_FROM
        self.bird = Bird(n, self.rng)
        self.time_left = float(level_time(n))
        self.next_extra = (score // EXTRA_LIFE_EVERY + 1) * EXTRA_LIFE_EVERY
        self.phase = "intro"
        self.t = 0.0
        self.invuln = 0.0
        self.paused = False
        self.clock = 0.0
        self.bonus_left = 0
        self.egg_total = len(self.level.eggs)

    # ------------------------------------------------------------------ logic
    def update(self, dt, inp):
        if inp.pause_pressed and self.phase in ("play", "ready"):
            self.paused = not self.paused
        if self.paused:
            if inp.quit_pressed:
                self.finish_run()
                self.app.change(TitleScene(self.app))
            return
        self.clock += dt
        getattr(self, "_" + self.phase)(dt, inp)

    def _intro(self, dt, inp):
        self.t += dt
        if self.t > 2.2 or inp.jump_pressed and self.t > 0.4:
            self.phase, self.t = "play", 0.0
            self.invuln = 0.6
            self.app.audio.play("start")

    def _ready(self, dt, inp):
        self.t += dt
        if self.t > 0.9:
            self.phase, self.t = "play", 0.0
            self.invuln = 1.6

    def _play(self, dt, inp):
        a = self.app.audio
        self.time_left -= dt
        self.invuln = max(0.0, self.invuln - dt)
        if int(self.time_left + dt) != int(self.time_left) and self.time_left < 10 and self.time_left > 0:
            a.play("tick")
        self.player.update(dt, inp, self.level, a)
        for h in self.hens:
            h.update(dt, self.level, self.player)
        if self.free_bird:
            before = self.bird.free
            self.bird.update(dt, self.player)
            if self.bird.free and not before:
                a.play("bird")

        # collectibles
        px, py = self.player.center()
        for cell in list(self.level.eggs):
            ex, ey = self.level.egg_pos(cell)
            if abs(px - ex) < 9 and abs(py - (ey - 5)) < 11:
                self.level.eggs.discard(cell)
                self.add_score(SCORE_EGG)
                a.play("egg")
        for cell in list(self.level.grain):
            ex, ey = self.level.egg_pos(cell)
            if abs(px - ex) < 9 and abs(py - (ey - 4)) < 11:
                self.level.grain.discard(cell)
                self.add_score(SCORE_GRAIN)
                a.play("grain")

        if not self.level.eggs:
            self.phase, self.t = "clear", 0.0
            self.bonus_left = int(self.time_left)
            self.add_score(SCORE_CLEAR)
            a.play("clear")
            return
        if self.time_left <= 0:
            self.die()
            return
        if self.invuln <= 0:
            pr = self.player.rect()
            if any(pr.colliderect(h.rect()) for h in self.hens) or (self.free_bird and self.bird.hits(self.player)):
                self.die()

    def die(self):
        self.phase, self.t = "dead", 0.0
        self.lives -= 1
        self.app.audio.play("die")

    def _dead(self, dt, inp):
        self.t += dt
        if self.t > 1.7:
            if self.lives <= 0:
                self.finish_run()
                self.app.change(GameOverScene(self.app, self.score, self.n))
                return
            self.player.reset(self.level)
            for h in self.hens:
                h.reset()
            self.bird.reset()
            self.time_left = max(self.time_left, 30.0)
            self.phase, self.t = "ready", 0.0

    def _clear(self, dt, inp):
        self.t += dt
        if self.bonus_left > 0 and self.t > 0.5:
            step = max(1, int(dt * 60))
            step = min(step, self.bonus_left)
            self.bonus_left -= step
            self.add_score(step * SCORE_TIME)
            if int(self.clock * 30) % 2 == 0:
                self.app.audio.play("tick")
        elif self.bonus_left <= 0 and self.t > 1.4:
            self.finish_run()
            if self.n >= NUM_LEVELS:
                self.app.change(WinScene(self.app, self.score))
            else:
                self.app.change(PlayScene(self.app, self.n + 1, self.score, self.lives))

    def add_score(self, pts):
        self.score += pts
        if self.score >= self.next_extra:
            self.next_extra += EXTRA_LIFE_EVERY
            self.lives += 1
            self.app.audio.play("life")

    def finish_run(self):
        self.app.record_score(self.score)

    # ------------------------------------------------------------------- draw
    def draw(self, s):
        sp = self.app.sprites
        s.blit(self.bg, (0, 0))
        # cage and bird
        if self.free_bird:
            s.blit(sp.cage_open, CAGE_RECT[:2])
        else:
            bob = math.sin(self.clock * (9 if int(self.clock) % 4 == 3 else 2.5)) * 2
            s.blit(sp.bird_small, (CAGE_CENTER[0] - 15, CAGE_CENTER[1] - 12 + bob))
            s.blit(sp.cage_shut, CAGE_RECT[:2])
        for cell in self.level.grain:
            x, y = self.level.egg_pos(cell)
            s.blit(sp.grain, (x - 8, y - 9))
        for i, cell in enumerate(sorted(self.level.eggs)):
            x, y = self.level.egg_pos(cell)
            glint = int(self.clock * 3 + i * 0.7) % 6 == 0
            s.blit(sp.egg[1 if glint else 0], (x - 5, y - 12))
        for h in self.hens:
            img = sp.hen[h.frame()]
            if h.dir < 0 and h.state != "climb":
                img = pygame.transform.flip(img, True, False)
            s.blit(img, (h.x - 10, h.y - 17))
        self.draw_player(s)
        if self.free_bird and self.phase != "intro":
            img = sp.bird[int(self.clock * 7) % 2]
            if self.bird.vx < -4:
                img = pygame.transform.flip(img, True, False)
            if self.bird.free or self.phase in ("play", "dead", "clear"):
                s.blit(img, (self.bird.x - 21, self.bird.y - 17))
        self.draw_hud(s)
        self.draw_overlay(s)

    def draw_player(self, s):
        p = self.player
        img = self.app.sprites.harry[p.frame()]
        if p.facing < 0 and p.state != "ladder":
            img = pygame.transform.flip(img, True, False)
        if self.phase == "dead":
            lift = math.sin(min(1.0, self.t / 1.0) * math.pi) * 22
            img = pygame.transform.rotate(pygame.transform.flip(img, False, True), self.t * 360)
            r = img.get_rect(center=(int(p.x), int(p.y - 11 - lift + max(0.0, self.t - 1.0) * 30)))
            s.blit(img, r)
            return
        if self.invuln > 0 and int(self.invuln * 14) % 2 == 0 and self.phase == "play":
            return
        s.blit(img, (p.x - 8, p.y - 23))

    def draw_hud(self, s):
        pygame.draw.rect(s, (14, 10, 28), (0, 0, W, OY))
        pygame.draw.line(s, (70, 56, 110), (0, OY - 1), (W, OY - 1))
        gfx.text(s, "SCORE %06d" % self.score, 16, (4, 8), GOLD, anchor="midleft")
        gfx.text(s, "HI %06d" % max(self.score, self.app.save["hi"]), 16, (112, 8), (200, 200, 235), anchor="midleft")
        gfx.text(s, "LV %02d" % self.n, 16, (186, 8), WHITE, anchor="midleft")
        t = max(0, int(math.ceil(self.time_left)))
        gfx.text(s, "T %03d" % t, 16, (224, 8), RED if t <= 10 else WHITE, anchor="midleft")
        hat = self.app.sprites.harry["idle"].subsurface((0, 0, 16, 9))
        for i in range(min(self.lives, 4)):
            s.blit(hat, (270 + i * 12, 3))
        if self.lives > 4:
            gfx.text(s, "+%d" % (self.lives - 4), 12, (W - 2, 8), WHITE, anchor="midright")

    def draw_overlay(self, s):
        cx = W // 2
        if self.phase == "intro":
            veil = pygame.Surface((W, 90), pygame.SRCALPHA)
            veil.fill((8, 4, 20, 190))
            s.blit(veil, (0, 100))
            gfx.text(s, "LEVEL %d" % self.n, 34, (cx, 124), GOLD)
            msg = ("THE BIG BIRD HAS ESCAPED!" if self.n == BIRD_FREE_FROM
                   else "THE BIG BIRD IS LOOSE!" if self.free_bird else "THE BIG BIRD IS CAGED... FOR NOW")
            gfx.text(s, msg, 18, (cx, 154), RED if self.free_bird else WHITE)
            gfx.text(s, "COLLECT ALL %d EGGS" % self.egg_total, 16, (cx, 174), (200, 220, 255))
        elif self.phase == "ready":
            gfx.text(s, "GET READY!", 26, (cx, 128), GOLD)
        elif self.phase == "dead" and self.lives <= 0 and self.t > 0.9:
            gfx.text(s, "GAME OVER", 30, (cx, 128), RED)
        elif self.phase == "clear":
            veil = pygame.Surface((W, 70), pygame.SRCALPHA)
            veil.fill((8, 4, 20, 190))
            s.blit(veil, (0, 104))
            gfx.text(s, "LEVEL %d CLEAR!" % self.n, 28, (cx, 124), GOLD)
            gfx.text(s, "TIME BONUS  %d" % self.bonus_left, 18, (cx, 150), WHITE)
        if self.paused:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((8, 4, 20, 170))
            s.blit(veil, (0, 0))
            gfx.text(s, "PAUSED", 34, (cx, 112), GOLD)
            gfx.text(s, "ESC: resume     Q: quit to title", 16, (cx, 146), WHITE)


class _EndScene:
    def __init__(self, app, score):
        self.app = app
        self.score = score
        self.level = Level(1)
        self.bg = gfx.render_level(self.level)
        self.t = 0.0

    def update(self, dt, inp):
        self.t += dt
        if self.t > 0.8 and (inp.jump_pressed or inp.pause_pressed):
            self.app.change(TitleScene(self.app))

    def panel(self, s):
        s.blit(self.bg, (0, 0))
        veil = pygame.Surface((W, 170), pygame.SRCALPHA)
        veil.fill((10, 6, 24, 190))
        s.blit(veil, (0, 56))


class GameOverScene(_EndScene):
    def __init__(self, app, score, level_no):
        super().__init__(app, score)
        self.level_no = level_no

    def draw(self, s):
        self.panel(s)
        gfx.text(s, "GAME OVER", 46, (W // 2, 92), RED)
        gfx.text(s, "You reached level %d" % self.level_no, 18, (W // 2, 128), WHITE)
        gfx.text(s, "SCORE %06d" % self.score, 26, (W // 2, 154), GOLD)
        if self.score >= self.app.save["hi"] and self.score > 0:
            gfx.text(s, "NEW HI-SCORE!", 18, (W // 2, 178), (120, 255, 140))
        if int(self.t * 2) % 2 == 0:
            gfx.text(s, "PRESS SPACE", 16, (W // 2, 204), (200, 200, 235))


class WinScene(_EndScene):
    def draw(self, s):
        self.panel(s)
        sp = self.app.sprites
        gfx.text(s, "YOU DID IT!", 44, (W // 2, 90), GOLD)
        gfx.text(s, "All 16 levels cleared. The big bird is beaten!", 16, (W // 2, 124), WHITE)
        gfx.text(s, "FINAL SCORE %06d" % self.score, 26, (W // 2, 152), GOLD)
        if int(self.t * 2) % 2 == 0:
            gfx.text(s, "PRESS SPACE", 16, (W // 2, 204), (200, 200, 235))
        hop = abs(math.sin(self.t * 5)) * 14
        gy = OY + GROUND_ROW * TILE
        for i, x in enumerate((60, 100, 220, 260)):
            s.blit(sp.egg[i % 2], (x, gy - 12 - hop * (1 if i % 2 else 0.6)))
        s.blit(sp.harry["jump" if hop > 3 else "idle"], (W // 2 - 8, gy - 23 - hop))
