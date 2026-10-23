"""The playable stage: camera, waves, combat resolution, effects, HUD and pause menu."""
import math
import random

import pygame

import gfx
from config import (W, H, FLOOR_Y, DEPTH, HUD_H, STAGES, ENEMIES, ITEMS, DIFF_TUNING, START_LIVES,
                    REMATCH_HP, Z_HIT)
from entities import Player, Enemy, Item, Vent, ATTACK_MOVES

WATER_Z = 49          # on the docks, feet deeper than this inside a gap are in the water


class GameScene:
    def __init__(self, app, stage_i, roster):
        self.app = app
        self.si = stage_i
        self.st = STAGES[stage_i]
        self.tune = DIFF_TUNING[app.save.get("diff", 1)]
        self.length = self.st["length"]
        self.bg = gfx.Background(self.st["theme"], self.length, self.st["hazards"])
        self.water = [(h[1], h[2]) for h in self.st["hazards"] if h[0] == "water"]
        self.vents = [Vent(self, h[1], h[2], i * 0.9) for i, h in enumerate(self.st["hazards"]) if h[0] == "vent"]
        self.cam = 0.0
        self.players = [None, None]
        for r in roster:
            p = Player(self, r["idx"], r["lives"], r["score"], 50 + r["idx"] * 36, 22 + r["idx"] * 20)
            self.players[r["idx"]] = p
        self.joined = {r["idx"] for r in roster}
        app.controls.shared = self.joined == {0}
        self.enemies = []
        self.items = [Item(self, k, x, z) for k, x, z in self.st["items"]]
        self.parts = []
        self.wave_i = 0
        self.wave = None
        self.go_t = 0.0
        self.time = float(self.st["time"])
        self.freeze_t = 0.0
        self.shake_t = 0.0
        self.shake_a = 0
        self.t = 0.0
        self.mode = "play"          # play | clear | over
        self.end_t = 0.0
        self.boss = None
        self.banner_t = 2.8
        self.boss_banner_t = 0.0
        self.time_over_t = 0.0
        self.paused = False
        self.pause_sel = 0
        self.hud_back = gfx.hud_back()
        app.audio.music(self.st["music"])

    # ======================================================================
    # services used by the entities
    # ======================================================================
    def sfx(self, name, vol=1.0):
        self.app.audio.play(name, vol)

    def freeze(self, t):
        self.freeze_t = max(self.freeze_t, t)

    def shake(self, t, a):
        self.shake_t = max(self.shake_t, t)
        self.shake_a = max(self.shake_a, a)

    def _part(self, **kw):
        kw.setdefault("t", 0.0)
        self.parts.append(kw)

    def spark(self, x, z, h, color=(255, 240, 180)):
        self._part(k="spark", x=x, z=z, h=h, life=0.14, color=color)

    def dust(self, x, z):
        for _ in range(5):
            self._part(k="dust", x=x + random.uniform(-10, 10), z=z, h=2, vx=random.uniform(-30, 30),
                       vh=random.uniform(10, 30), life=0.45)

    def puff(self, x, z, h, small=False):
        self._part(k="steam", x=x, z=z, h=h, vx=random.uniform(-8, 8), vh=random.uniform(50, 80) if not small else 20,
                   life=0.7 if not small else 0.35, r=random.randint(4, 7) if not small else 2)

    def splash(self, x, z):
        self.sfx("splash")
        for _ in range(12):
            self._part(k="drop", x=x + random.uniform(-6, 6), z=z, h=0, vx=random.uniform(-40, 40),
                       vh=random.uniform(80, 170), life=0.8)

    def debris(self, x, z, h, kind):
        for i in range(7):
            self._part(k="bit", x=x, z=z, h=h, vx=random.uniform(-70, 70), vh=random.uniform(60, 150), life=0.9,
                       img=gfx.prop("plank", i) if kind == "plank" else gfx.prop(kind))
            if kind != "plank":
                break

    def popup(self, x, z, h, s, color):
        self._part(k="text", x=x, z=z, h=h, s=s, color=color, life=1.0)

    def live_players(self):
        return [p for p in self.players if p is not None and not p.out]

    def nearest_player(self, e):
        best, bd = None, 1e9
        for p in self.live_players():
            if p.state in ("dead", "drop", "sink", "out"):
                continue
            if p.state == "held" and p.held_by is not e:
                d = 1e6 + abs(p.x - e.x)
            else:
                d = abs(p.x - e.x) + abs(p.z - e.z) * 2
            if d < bd:
                best, bd = p, d
        return best

    def attackers(self):
        return sum(1 for e in self.enemies if e.script is not None and e.script_name in ATTACK_MOVES)

    def in_water(self, x, z):
        if z <= WATER_Z:
            return False
        return any(a < x < b for a, b in self.water)

    def safe_z(self, x, z):
        if self.water and z > WATER_Z - 3 and any(a - 14 < x < b + 14 for a, b in self.water):
            return WATER_Z - 3
        return z

    def melee(self, attacker, rect, dmg, kd, targets, hitset, sfx, both=False):
        n = 0
        rects = [attacker.world_rect(rect)]
        if both:
            rects.append(attacker.world_rect(rect, mirror=True))
        for tgt in targets:
            if tgt is attacker or tgt in hitset or not tgt.can_be_hit():
                continue
            for x0, x1, h0, h1 in rects:
                if tgt.body_overlap(x0, x1, h0, h1, attacker.z, Z_HIT * max(1.0, attacker.scale)):
                    hitset.add(tgt)
                    dirx = 1 if tgt.x >= attacker.x else -1
                    if not both:
                        dirx = attacker.face if rect[0] >= 0 else -attacker.face
                    tgt.take_hit(max(1, int(round(dmg))), kd, dirx, attacker, sfx)
                    self.spark((tgt.x + attacker.x) / 2 + dirx * 4, tgt.z, attacker.y + (-rect[2] - rect[3]) / 2 *
                               attacker.scale)
                    n += 1
                    break
        return n

    def quake(self, src, radius, dmg):
        for p in self.live_players():
            if p.can_be_hit() and p.y < 4 and abs(p.x - src.x) < radius and abs(p.z - src.z) < 26:
                p.take_hit(dmg, True, 1 if p.x >= src.x else -1, src, "hit")

    def item_at(self, p):
        best = None
        for it in self.items:
            if it.state == "ground" and it.y <= 1 and not it.remove and ITEMS[it.kind]["kind"] in ("melee", "throw", "heavy") \
                    and abs(it.x - p.x) < 14 and abs(it.z - p.z) < 9:
                best = it
        return best

    def enemy_behind_only(self, p):
        front = behind = False
        for e in self.enemies:
            if not e.can_be_hit() or abs(e.z - p.z) > Z_HIT:
                continue
            d = (e.x - p.x) * p.face
            if 0 < d < 34:
                front = True
            elif -28 < d <= 0:
                behind = True
        return behind and not front

    def grab_target(self, p, dx):
        for e in self.enemies:
            if e.e.get("grab") and e.state == "hurt" and e.hp > 0 and abs(e.z - p.z) < 6 \
                    and 0 < (e.x - p.x) * dx < 18:
                return e
        return None

    def try_enemy_grab(self, e, rect):
        x0, x1, h0, h1 = e.world_rect(rect)
        for p in self.live_players():
            if p.can_be_hit() and p.state in ("idle", "walk", "attack") and p.y <= 0 \
                    and p.body_overlap(x0, x1, h0, h1, e.z, 7):
                return p
        return None

    def spawn_enemy(self, kind, side, boss_wave=False):
        x = self.cam - 24 if side == "L" else self.cam + W + 24
        z = self.safe_z(x, random.uniform(6, DEPTH - 6))
        hp_mul = REMATCH_HP if ENEMIES[kind].get("boss") and not boss_wave else 1.0
        e = Enemy(self, kind, x, z, 1 if side == "L" else -1, hp_mul)
        self.enemies.append(e)
        return e

    def enemy_killed(self, e):
        killer = e.last_hitter if (e.last_hitter is not None and e.last_hitter.is_player) else None
        if killer is None:
            lp = self.live_players()
            killer = lp[0] if lp else None
        if killer is not None:
            killer.add_score(e.e["score"])
            self.popup(e.x, e.z, 40 * e.scale, str(e.e["score"]), (255, 230, 120))
        if e.kind == "knifer" and random.random() < 0.5:
            self.items.append(Item(self, "knife", e.x, e.z, 10))
        elif not e.boss and random.random() < 0.08:
            self.items.append(Item(self, random.choice(("soda", "cash", "chicken")), e.x, e.z, 10))
        if e is self.boss:
            self.stage_clear()

    def on_player_out(self, p):
        if not self.live_players():
            self.mode = "over"
            self.end_t = 0.0
            self.app.audio.music(None)
            self.sfx("lose")

    # ======================================================================
    # flow
    # ======================================================================
    def stage_clear(self):
        self.mode = "clear"
        self.end_t = 0.0
        self.app.audio.music(None)
        self.sfx("win")
        for e in self.enemies:
            if e is not self.boss and e.state not in ("dead",):
                e.hp = 0
                e.last_hitter = None
                e.knockdown(1 if e.x > self.boss.x else -1, 1.2)
        for p in self.live_players():
            p.release_all()

    def roster(self):
        return [dict(idx=p.idx, lives=p.lives, score=p.score) for p in self.players if p is not None and not p.out]

    def revive_all(self):
        """Continue: everyone who has played comes back with fresh lives (score resets)."""
        for idx in sorted(self.joined):
            p = Player(self, idx, START_LIVES, 0, self.cam + 60 + idx * 40, DEPTH / 2)
            p.respawn()
            self.players[idx] = p
        self.mode = "play"
        self.app.audio.music("boss" if self.boss is not None else self.st["music"])

    def join(self, idx):
        p = Player(self, idx, START_LIVES, 0, self.cam + 60 + idx * 40, DEPTH / 2)
        p.respawn()
        self.players[idx] = p
        self.joined.add(idx)
        self.app.controls.shared = self.joined == {0}
        self.sfx("coin")

    def handle(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p):
                self.paused = not self.paused
                self.pause_sel = 0
                self.sfx("select")

    def update(self, dt):
        c = self.app.controls
        if self.paused:
            if c.menu_pressed("up") or c.menu_pressed("down"):
                self.pause_sel = 1 - self.pause_sel
                self.sfx("blip")
            if c.confirm():
                if self.pause_sel == 0:
                    self.paused = False
                else:
                    self.app.update_hi(max((p.score for p in self.players if p), default=0), self.si)
                    from scenes import TitleScene
                    self.app.change(TitleScene(self.app))
                self.sfx("select")
            return
        if any(p.pressed("start") for p in c.pads) and self.mode == "play":
            for idx in (0, 1):
                pl = self.players[idx]
                if c.pads[idx].pressed("start") and (pl is None or pl.out) and (idx == 1 or pl is not None):
                    self.join(idx)
                    break
            else:
                if c.pads[0].pressed("start") and self.players[0] is not None and not self.players[0].out:
                    self.paused = True
                    self.pause_sel = 0
                    self.sfx("select")
                    return
        self.t += dt
        self.banner_t = max(0.0, self.banner_t - dt)
        self.boss_banner_t = max(0.0, self.boss_banner_t - dt)
        self.go_t = max(0.0, self.go_t - dt)
        self.time_over_t = max(0.0, self.time_over_t - dt)
        self.shake_t = max(0.0, self.shake_t - dt)
        if self.shake_t <= 0:
            self.shake_a = 0
        self.update_parts(dt)
        if self.freeze_t > 0:
            self.freeze_t -= dt
            return
        for p in self.players:
            if p is not None:
                p.update(dt)
        for e in self.enemies:
            e.update(dt)
            e.update_entering(self.cam)
        for it in self.items:
            it.update(dt)
        for v in self.vents:
            v.update(dt)
        self.enemies = [e for e in self.enemies if not e.remove]
        self.items = [it for it in self.items if not it.remove]
        self.pickup_food()
        self.clamp()
        self.update_camera(dt)
        if self.mode == "play":
            self.update_waves(dt)
            if self.boss_banner_t <= 0 and self.banner_t <= 0:
                self.time -= dt
            if self.time <= 0:
                self.time = 60.0
                self.time_over_t = 2.0
                for p in self.live_players():
                    if p.state not in ("dead", "drop"):
                        p.release_all()
                        p.hp = 0
                        p.set_state("dead")
                self.sfx("lose")
        elif self.mode == "clear":
            self.end_t += dt
            if self.end_t > 1.4:
                for p in self.live_players():
                    if p.state in ("idle", "walk"):
                        p.pose = "victory" if p.idx == 0 else "pump"
                        p.weapon = None if p.heavy() else p.weapon
            if self.end_t > 4.0:
                from scenes import StageClearScene
                self.app.change(StageClearScene(self.app, self.si, self.roster(), int(self.time),
                                                [p for p in self.live_players()]))
        elif self.mode == "over":
            self.end_t += dt
            if self.end_t > 1.5:
                from scenes import ContinueScene
                self.app.change(ContinueScene(self.app, self))

    def pickup_food(self):
        for it in self.items:
            info = ITEMS.get(it.kind, {})
            if it.state != "ground" or info.get("kind") not in ("food", "cash") or it.remove or it.y > 2:
                continue
            for p in self.live_players():
                if p.state in ("idle", "walk") and abs(p.x - it.x) < 12 and abs(p.z - it.z) < 8:
                    it.remove = True
                    if info["kind"] == "food":
                        p.hp = min(p.maxhp, p.hp + info["heal"])
                        self.sfx("eat")
                        self.popup(it.x, it.z, 30, "+%d HP" % info["heal"], (140, 255, 140))
                    else:
                        p.add_score(info["pts"])
                        self.sfx("coin")
                        self.popup(it.x, it.z, 30, str(info["pts"]), (255, 230, 120))
                    break

    def clamp(self):
        lo, hi = self.cam + 10, min(self.cam + W - 10, self.length - 10)
        for p in self.live_players():
            p.x = max(lo, min(hi, p.x))
            p.z = max(0.0, min(DEPTH, p.z))
        for e in self.enemies:
            if not e.entering:
                e.x = max(self.cam + 6, min(self.cam + W - 6, e.x))
            e.z = max(0.0, min(DEPTH, e.z))

    def cam_max(self):
        if self.wave is not None:
            return float(self.wave["lock"])
        if self.wave_i < len(self.st["waves"]):
            return float(self.st["waves"][self.wave_i][0])
        return float(self.length - W)

    def update_camera(self, dt):
        act = [p for p in self.live_players() if p.state not in ("dead", "sink")]
        if not act:
            return
        target = sum(p.x for p in act) / len(act) - W * 0.42
        target = min(target, min(p.x for p in act) - 14, self.cam_max(), self.length - W)
        if target > self.cam:
            self.cam = min(target, self.cam + max(40.0, (target - self.cam) * 6) * dt)

    def update_waves(self, dt):
        waves = self.st["waves"]
        if self.wave is None:
            if self.wave_i >= len(waves):
                return
            lock, spawns, boss = waves[self.wave_i]
            if self.cam >= lock - 0.5:
                self.wave = dict(lock=lock, queue=sorted(((d, k, s) for k, s, d in spawns)), t=0.0, boss=boss)
                self.go_t = 0.0
            return
        w = self.wave
        w["t"] += dt
        while w["queue"] and w["queue"][0][0] <= w["t"]:
            _, kind, side = w["queue"].pop(0)
            e = self.spawn_enemy(kind, side, boss_wave=w["boss"])
            if w["boss"] and ENEMIES[kind].get("boss") and self.boss is None:
                self.boss = e
                self.boss_banner_t = 3.0
                self.sfx("roar")
                self.app.audio.music("boss")
        alive = [e for e in self.enemies if e.state != "dead"]
        if not w["queue"] and not alive and self.mode == "play":
            self.wave = None
            self.wave_i += 1
            if self.wave_i < len(waves):
                self.go_t = 3.0
                self.sfx("go")

    def update_parts(self, dt):
        keep = []
        for p in self.parts:
            p["t"] += dt
            if p["t"] >= p["life"]:
                continue
            k = p["k"]
            if k in ("dust", "steam"):
                p["x"] += p["vx"] * dt
                p["h"] += p["vh"] * dt
                p["vh"] *= (1 - 2.5 * dt)
            elif k in ("drop", "bit"):
                p["x"] += p["vx"] * dt
                p["vh"] -= 600 * dt
                p["h"] = max(0.0, p["h"] + p["vh"] * dt)
            elif k == "text":
                p["h"] += 24 * dt
            keep.append(p)
        self.parts = keep

    # ======================================================================
    # drawing
    # ======================================================================
    def draw(self, surf):
        ox = random.randint(-self.shake_a, self.shake_a) if self.shake_t > 0 else 0
        oy = random.randint(-self.shake_a, self.shake_a) if self.shake_t > 0 else 0
        cam = self.cam + ox
        self.bg.draw(surf, cam, self.t)
        for v in self.vents:
            gfx.draw_vent(surf, int(v.x - cam), int(FLOOR_Y + v.z + oy), v.state())
        drawables = [p for p in self.players if p is not None and not p.out] + self.enemies + self.items
        for d in drawables:
            d.draw_shadow(surf, cam)
        drawables.sort(key=lambda d: (d.z, 0 if isinstance(d, Item) else 1))
        for d in drawables:
            d.draw(surf, cam)
        self.draw_parts(surf, cam)
        self.draw_hud(surf)
        self.draw_banners(surf)

    def draw_parts(self, surf, cam):
        for p in self.parts:
            sx, sy = int(p["x"] - cam), int(FLOOR_Y + p["z"] - p["h"])
            k = p["k"]
            f = p["t"] / p["life"]
            if k == "spark":
                img = gfx.impact_star(max(3, int(9 * (1 - f))), p["color"])
                surf.blit(img, img.get_rect(center=(sx, sy)))
            elif k == "dust":
                surf.blit(gfx.soft_circle(3, (200, 190, 170), int(150 * (1 - f))), (sx - 3, sy - 3))
            elif k == "steam":
                r = int(p["r"] + f * 8)
                surf.blit(gfx.soft_circle(r, (235, 240, 245), int(170 * (1 - f))), (sx - r, sy - r))
            elif k == "drop":
                surf.fill((150, 200, 255), (sx, sy, 2, 2))
            elif k == "bit":
                surf.blit(p["img"], (sx, sy - 4))
            elif k == "text":
                gfx.text(surf, p["s"], 7, (sx, sy), p["color"], outline=True)

    def draw_hud(self, surf):
        surf.blit(self.hud_back, (0, 0))
        for idx in (0, 1):
            p = self.players[idx]
            x0 = 6 if idx == 0 else W - 126
            if p is None or p.out:
                if int(self.t * 2) % 2 == 0:
                    msg = "PRESS START" if idx == 0 else "2P PRESS START"
                    gfx.text(surf, msg, 7, (x0 + 60, 9), (255, 230, 120), outline=True)
                    gfx.text(surf, "ENTER" if idx == 0 else "RIGHT SHIFT", 7, (x0 + 60, 20), (170, 160, 200),
                             outline=True)
                continue
            gfx.text(surf, p.name, 7, (x0, 3), p.color, anchor="topleft", outline=True)
            gfx.text(surf, "x%d" % max(0, p.lives), 7, (x0 + 30, 3), (240, 240, 240), anchor="topleft", outline=True)
            gfx.text(surf, "%07d" % p.score, 7, (x0 + 120, 3), (255, 255, 255), anchor="topright", outline=True)
            frac = p.hp / p.maxhp
            col = (90, 230, 110) if frac > 0.5 else (250, 210, 60) if frac > 0.25 else (250, 70, 60)
            gfx.energy_bar(surf, x0, 13, 118, 5, frac, col, segs=16)
            if p.weapon:
                gfx.text(surf, p.weapon.upper(), 7, (x0 + 120, 21), (200, 200, 220), anchor="topright", outline=True)
            e = p.last_enemy
            if e is not None and p.last_enemy_t > 0 and e is not self.boss:
                gfx.text(surf, e.name, 7, (x0, 21), (255, 170, 170), anchor="topleft", outline=True)
                gfx.energy_bar(surf, x0 + 42, 22, 60, 4, max(0, e.hp) / e.maxhp, (240, 90, 80))
        tcol = (255, 255, 255) if self.time > 20 or int(self.t * 4) % 2 else (255, 80, 80)
        gfx.text(surf, "%02d" % max(0, int(self.time)), 20, (W // 2, 11), tcol, outline=True)
        gfx.text(surf, "STAGE %d" % (self.si + 1), 7, (W // 2, 23), (200, 170, 255), outline=True)
        b = self.boss
        if b is not None and not b.remove and self.mode == "play":
            gfx.text(surf, b.name, 7, (40, H - 12), (255, 120, 120), anchor="topleft", outline=True)
            gfx.energy_bar(surf, 86, H - 11, 190, 5, max(0, b.hp) / b.maxhp, (230, 60, 70), segs=20)

    def draw_banners(self, surf):
        if self.banner_t > 0 and self.mode == "play":
            a = min(1.0, self.banner_t / 0.4)
            y = 84 if a >= 1 else int(84 - (1 - a) * 30)
            img = gfx.fancy_text("STAGE %d" % (self.si + 1), 30, (255, 240, 160), (240, 90, 60))
            surf.blit(img, img.get_rect(center=(W // 2, y)))
            gfx.text(surf, self.st["name"], 13, (W // 2, y + 22), (255, 255, 255), outline=True)
        if self.go_t > 0:
            gfx.go_arrow(surf, self.go_t)
        if self.boss_banner_t > 0 and self.boss is not None:
            b = self.boss
            band = pygame.Surface((W, 52), pygame.SRCALPHA)
            band.fill((0, 0, 0, 170))
            surf.blit(band, (0, 64))
            img = gfx.fancy_text(b.name, 26, (255, 200, 200), (220, 40, 60))
            surf.blit(img, img.get_rect(center=(W // 2, 80)))
            gfx.text(surf, b.e.get("title", ""), 7, (W // 2, 96), (255, 220, 140), outline=True)
            gfx.text(surf, '"%s"' % b.e.get("quote", ""), 7, (W // 2, 107), (230, 230, 240), outline=True)
        if self.time_over_t > 0:
            gfx.text(surf, "TIME OVER", 20, (W // 2, 90), (255, 90, 90), outline=True)
        if self.mode == "clear" and self.end_t > 1.0:
            img = gfx.fancy_text("STAGE CLEAR!", 30, (255, 250, 180), (250, 140, 40))
            surf.blit(img, img.get_rect(center=(W // 2, 80)))
        if self.mode == "over":
            gfx.text(surf, "GAME OVER", 20, (W // 2, 90), (255, 90, 90), outline=True)
        if self.paused:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 150))
            surf.blit(veil, (0, 0))
            gfx.text(surf, "PAUSED", 20, (W // 2, 80), (255, 230, 120), outline=True)
            for i, s in enumerate(("RESUME", "QUIT TO TITLE")):
                col = (255, 255, 255) if i == self.pause_sel else (150, 140, 170)
                gfx.text(surf, ("> " if i == self.pause_sel else "") + s, 7, (W // 2, 108 + i * 14), col, outline=True)
