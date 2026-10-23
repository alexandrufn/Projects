"""Fighters (players, street gang, bosses), items, projectiles and hazards.

Positions: x along the street, z into the screen (0 = back wall, DEPTH = front curb), y = height
above the ground. Feet are drawn at screen (x - cam, FLOOR_Y + z - y).
"""
import math
import random

import pygame

import gfx
from config import (W, FLOOR_Y, DEPTH, GRAVITY, JUMP_V, PLAYER_HP, EXTRA_LIFE_EVERY, PLAYERS, ATTACKS,
                    PUNCH_CHAIN, KICK_CHAIN, ITEMS, CHARS, ENEMIES, Z_HIT)


def H(rect, dmg, kd=False, sfx="punch", both=False):
    return dict(rect=rect, dmg=dmg, kd=kd, sfx=sfx, both=both)


# Enemy and boss move scripts: a list of (pose, duration, options).
#   v: forward speed   jump: take-off speed (step lasts until landing)   seek: aim the jump at the target
#   hit: active hitbox  rehit: clear the hit list every n seconds  armor: can't be interrupted
#   grab: try to grab the target   spawn: projectile   quake: shockwave on landing   track: follow target depth
MOVES = {
    "jab": [("punch_w", 0.22, {}), ("punch", 0.14, {"hit": H((4, 25, -38, -27), 4)}), ("idle", 0.30, {})],
    "kick": [("kick_w", 0.26, {}), ("kick", 0.16, {"hit": H((6, 30, -40, -24), 5, sfx="kick")}), ("idle", 0.34, {})],
    "lunge": [("dash_w", 0.30, {}), ("dash", 0.26, {"v": 150, "hit": H((4, 26, -36, -20), 5, True, "hit")}),
              ("idle", 0.40, {})],
    "bat": [("swing_w", 0.34, {}), ("swing", 0.16, {"hit": H((4, 36, -48, -16), 7, True, "bat")}), ("idle", 0.42, {})],
    "grab": [("grab", 0.30, {"grab": (2, 22, -42, -16)}), ("idle", 0.30, {})],
    "headbutt": [("punch_w", 0.30, {}), ("headbutt", 0.16, {"v": 40, "hit": H((4, 22, -48, -30), 6, False, "hit")}),
                 ("idle", 0.36, {})],
    "slam": [("slam_w", 0.42, {"armor": True}), ("slam", 0.18, {"hit": H((0, 30, -40, -2), 8, True, "hit")}),
             ("slam", 0.30, {}), ("idle", 0.30, {})],
    "throwknife": [("throw_hi", 0.38, {}), ("throw", 0.22, {"spawn": "eknife"}), ("idle", 0.50, {})],
    "slash": [("stab_w", 0.24, {}), ("stab", 0.14, {"hit": H((4, 28, -38, -24), 6, False, "slash")}),
              ("idle", 0.36, {})],
    "whip": [("whip_w", 0.34, {}), ("whip", 0.20, {"hit": H((10, 56, -42, -24), 6, False, "whip")}),
             ("idle", 0.36, {})],
    "whip2": [("whip_w", 0.26, {}), ("whip", 0.16, {"hit": H((10, 56, -42, -24), 5, False, "whip")}),
              ("whip_w", 0.16, {}), ("whip", 0.20, {"hit": H((10, 58, -42, -24), 7, True, "whip")}),
              ("idle", 0.40, {})],
    "spinwhip": [("chainspin", 0.30, {"armor": True, "sfx": "whoosh", "anim": 2}),
                 ("chainspin", 0.90, {"armor": True, "anim": 3, "rehit": 0.3, "track": 30,
                                      "hit": H((-46, 46, -44, -14), 6, True, "whip", both=True)}),
                 ("idle", 0.45, {})],
    "flip": [("crouch", 0.12, {}), ("jump", 0.9, {"jump": 210, "v": -120}), ("idle", 0.20, {})],
    "charge": [("dash_w", 0.50, {"armor": True, "sfx": "roar"}),
               ("dash", 0.70, {"armor": True, "v": 215, "hit": H((0, 26, -48, -8), 9, True, "hit")}),
               ("idle", 0.60, {})],
    "stomp": [("crouch", 0.30, {"armor": True}), ("jump", 1.2, {"jump": 270, "seek": True, "armor": True}),
              ("slam", 0.40, {"quake": True, "armor": True}), ("idle", 0.40, {})],
    "dashslash": [("dash_w", 0.36, {"armor": True}),
                  ("dash", 0.34, {"armor": True, "v": 235, "hit": H((0, 32, -42, -16), 8, True, "slash")}),
                  ("idle", 0.45, {})],
    "fan": [("throw_hi", 0.40, {}), ("throw", 0.30, {"spawn": "fan"}), ("idle", 0.50, {})],
    "stars": [("throw_hi", 0.36, {}), ("throw", 0.30, {"spawn": "stars"}), ("idle", 0.50, {})],
    "slash3": [("stab_w", 0.18, {}), ("stab", 0.10, {"hit": H((4, 30, -38, -24), 4, False, "slash")}),
               ("stab_w", 0.10, {}), ("stab", 0.10, {"hit": H((4, 30, -38, -24), 4, False, "slash")}),
               ("swing_w", 0.14, {}), ("swing", 0.14, {"hit": H((4, 34, -48, -16), 7, True, "slash")}),
               ("idle", 0.45, {})],
    "jumpstab": [("crouch", 0.20, {}),
                 ("swing", 1.2, {"jump": 230, "seek": True, "hit": H((0, 32, -40, -4), 8, True, "slash")}),
                 ("idle", 0.40, {})],
    "katana": [("swing_w", 0.30, {}), ("swing", 0.14, {"hit": H((4, 46, -52, -12), 9, True, "slash")}),
               ("idle", 0.40, {})],
    "katana3": [("stab_w", 0.20, {}), ("stab", 0.12, {"v": 60, "hit": H((4, 40, -40, -24), 5, False, "slash")}),
                ("swing_w", 0.14, {}), ("swing", 0.12, {"v": 60, "hit": H((4, 44, -50, -14), 5, False, "slash")}),
                ("swing_w", 0.16, {"armor": True}),
                ("swing", 0.16, {"v": 80, "hit": H((4, 46, -52, -12), 9, True, "slash")}), ("idle", 0.50, {})],
    "roar": [("victory", 0.9, {"armor": True, "sfx": "roar"}), ("idle", 0.2, {})],
    "summon": [("taunt", 1.0, {"armor": True, "summon": 2, "anim": 2}), ("idle", 0.2, {})],
}
ATTACK_MOVES = set(MOVES) - {"flip", "roar", "summon"}
UNARMED = [("jab", 5, 0, 30), ("kick", 3, 0, 34)]


class Fighter:
    is_player = False
    boss = False

    def __init__(self, game, ckey, x, z, face):
        self.game = game
        self.ckey = ckey
        self.cdef = CHARS[ckey]
        self.scale = self.cdef["scale"]
        self.x, self.z, self.y = float(x), float(z), 0.0
        self.vx = self.vz = self.vy = 0.0
        self.face = face
        self.state = "idle"
        self.t = 0.0
        self.pose = "idle"
        self.ph = 0.0
        self.flash = 0.0
        self.invuln = 0.0
        self.hp = self.maxhp = 1
        self.weapon = None
        self.remove = False
        self.bounced = False
        self.thrown_by = None
        self.thrown_hits = set()
        self.combo_hits = 0
        self.combo_t = 0.0
        self.holding = None
        self.held_by = None
        self.last_hitter = None
        self.name = ""

    # --- helpers ---------------------------------------------------------
    def set_state(self, s):
        self.state = s
        self.t = 0.0

    def can_be_hit(self):
        return (not self.remove and self.invuln <= 0 and self.hp > 0
                and self.state not in ("fall", "down", "getup", "dead", "out", "sink", "drop"))

    def body_overlap(self, x0, x1, h0, h1, z, zr=Z_HIT):
        if abs(z - self.z) > zr + 2 * (self.scale - 1) * 6:
            return False
        hw = 8 * self.scale
        if x1 < self.x - hw or x0 > self.x + hw:
            return False
        return not (h1 < self.y or h0 > self.y + 46 * self.scale)

    def world_rect(self, rect, mirror=False):
        x0, x1, y0, y1 = rect
        s = self.scale
        f = -self.face if mirror else self.face
        if f > 0:
            X0, X1 = self.x + x0 * s, self.x + x1 * s
        else:
            X0, X1 = self.x - x1 * s, self.x - x0 * s
        return X0, X1, self.y - y1 * s, self.y - y0 * s

    def drop_weapon(self):
        w = self.weapon
        if w and w in ITEMS and ITEMS[w]["kind"] in ("melee", "throw", "heavy"):
            it = Item(self.game, w, self.x + self.face * 6, self.z, y=20)
            it.vy = 120
            it.vx = -self.face * 30
            if self.is_player:
                it.uses = getattr(self, "uses", 0) or None
            self.game.items.append(it)
            self.weapon = None

    def release_all(self):
        if self.holding is not None:
            h = self.holding
            self.holding = None
            if h.held_by is self:
                h.held_by = None
                if h.state in ("held", "grabbed"):
                    h.set_state("hurt")
        if self.held_by is not None:
            hb = self.held_by
            self.held_by = None
            if hb.holding is self:
                hb.holding = None
                if hb.state in ("hold", "grab"):
                    hb.set_state("idle")

    def take_hit(self, dmg, kd, dirx, src=None, sfx="punch"):
        g = self.game
        self.release_all()
        self.hp -= dmg
        self.flash = 0.08
        self.combo_hits += 1
        self.combo_t = 0.9
        self.last_hitter = src
        g.sfx(sfx)
        g.freeze(0.06 if kd else 0.035)
        if src is not None and src.is_player and not self.is_player:
            src.add_score(int(dmg * 10))
            src.last_enemy, src.last_enemy_t = self, 2.5
        limit = 3 if self.is_player else 4
        armored = getattr(self, "armored", lambda: False)()
        if self.hp <= 0 or ((kd or self.combo_hits >= limit) and not armored):
            self.knockdown(dirx, 1.0 + (0.3 if self.hp <= 0 else 0))
        elif not armored:
            if hasattr(self, "script"):
                self.script = None
            self.set_state("hurt")
            self.pose = random.choice(("hurt", "hurt2"))
            self.x += dirx * 3
            self.face = -dirx if dirx else self.face

    def knockdown(self, dirx, power=1.0):
        self.release_all()
        if hasattr(self, "script"):
            self.script = None
        self.set_state("fall")
        self.combo_hits = 0
        self.vx = dirx * 85 * power
        self.vz = 0.0
        self.vy = 165 + 40 * (power - 1)
        self.y = max(self.y, 1.0)
        self.bounced = False
        if dirx:
            self.face = -dirx
        self.game.sfx("hurt" if self.is_player else "whoosh", 0.6)
        if self.is_player or (self.weapon in ("bat", "pipe")):
            self.drop_weapon()

    def update_fall(self, dt):
        g = self.game
        if self.state == "fall":
            self.x += self.vx * dt
            self.z = max(0.0, min(DEPTH, self.z + self.vz * dt))
            self.vy -= GRAVITY * dt
            self.y += self.vy * dt
            self.pose = "fall" if not self.bounced else "lie"
            if self.thrown_by is not None and abs(self.vx) > 60:
                for e in g.enemies:
                    if e is not self and e not in self.thrown_hits and e.can_be_hit() and \
                            e.body_overlap(self.x - 10, self.x + 10, self.y, self.y + 30, self.z, 10):
                        self.thrown_hits.add(e)
                        e.take_hit(7, True, 1 if self.vx > 0 else -1, self.thrown_by, "hit")
            if self.y <= 0:
                self.y = 0.0
                if g.in_water(self.x, self.z):
                    self.splash()
                    return
                if not self.bounced:
                    self.bounced = True
                    self.vy = 70
                    self.vx *= 0.4
                    self.y = 0.1
                    g.sfx("thud", 0.8)
                    g.dust(self.x, self.z)
                    if self.scale > 1.25:
                        g.shake(0.25, 3)
                else:
                    self.set_state("down")
                    self.vx = 0.0
                    self.thrown_by = None
                    self.thrown_hits = set()
        elif self.state == "down":
            self.pose = "lie"
            if self.t > (0.9 if self.is_player else 0.75):
                if self.hp <= 0:
                    self.set_state("dead")
                    self.on_dead()
                else:
                    self.set_state("getup")
        elif self.state == "getup":
            self.pose = "getup"
            if self.t > 0.35:
                self.set_state("idle")
                self.invuln = 0.7 if self.is_player else 0.25

    def splash(self):
        self.game.splash(self.x, self.z)

    def on_dead(self):
        pass

    # --- drawing ---------------------------------------------------------
    def draw_shadow(self, surf, cam):
        w = int(24 * self.scale) - min(10, int(self.y / 6))
        if self.state in ("down", "dead") or self.pose == "lie":
            w = int(40 * self.scale)
        img = gfx.soft_ellipse(max(6, w), 6, (0, 0, 0), 90)
        surf.blit(img, (int(self.x - cam - img.get_width() / 2), int(FLOOR_Y + self.z - 3)))

    def visible(self):
        if self.state == "dead":
            return int(self.t * 14) % 2 == 0
        if self.invuln > 0 and self.state not in ("getup",):
            return int(self.invuln * 20) % 2 == 0
        return True

    def draw(self, surf, cam):
        if not self.visible():
            return
        img, (ax, ay) = gfx.frame(self.ckey, self.cdef, self.pose, self.ph, self.face < 0, self.weapon)
        if self.flash > 0:
            img = gfx.white(img)
        surf.blit(img, (int(round(self.x - cam)) - ax, int(round(FLOOR_Y + self.z - self.y)) - ay))


# ============================================================================
# Players
# ============================================================================
class Player(Fighter):
    is_player = True

    def __init__(self, game, idx, lives, score, x, z):
        ckey = ("kai", "vera")[idx]
        super().__init__(game, ckey, x, z, 1)
        st = PLAYERS[ckey]
        self.idx = idx
        self.name = st["name"]
        self.speed = st["speed"]
        self.power = st["power"]
        self.color = st["color"]
        self.hp = self.maxhp = PLAYER_HP
        self.lives = lives
        self.score = score
        self.next_life = (score // EXTRA_LIFE_EVERY + 1) * EXTRA_LIFE_EVERY
        self.pad = game.app.controls.pads[idx]
        self.atk = None
        self.atk_hits = set()
        self.atk_fired = False
        self.chain_t = 0.0
        self.chain_kind = None
        self.chain_i = 0
        self.out = False
        self.grab_n = 0
        self.knee_t = 0.0
        self.escape = 0.0
        self.last_dx = 0
        self.last_enemy = None
        self.last_enemy_t = 0.0
        self.uses = 0
        self.jvx = self.jvz = 0.0

    def add_score(self, n):
        self.score += n
        while self.score >= self.next_life:
            self.next_life += EXTRA_LIFE_EVERY
            self.lives += 1
            self.game.sfx("coin")
            self.game.popup(self.x, self.z, 60, "1UP", (120, 255, 120))

    # --- update ----------------------------------------------------------
    def update(self, dt):
        self.t += dt
        for a in ("invuln", "flash", "chain_t", "last_enemy_t", "combo_t"):
            setattr(self, a, max(0.0, getattr(self, a) - dt))
        if self.combo_t <= 0:
            self.combo_hits = 0
        if self.out:
            return
        st = self.state
        if st in ("fall", "down", "getup"):
            self.update_fall(dt)
            return
        if st == "dead":
            self.pose = "lie"
            if self.t > 1.6:
                self.lose_life()
            return
        if st == "sink":
            self.y -= 50 * dt
            self.pose = "fall"
            if self.t > 0.8:
                self.hp -= 20
                if self.hp <= 0:
                    self.hp = 0
                    self.lose_life()
                else:
                    self.y = 0
                    self.z = 26
                    self.x = self.game.cam + 60
                    self.set_state("drop")
                    self.y = 120
                    self.vy = 0
                    self.invuln = 2.0
            return
        if st == "drop":
            self.vy -= GRAVITY * 0.6 * dt
            self.y += self.vy * dt
            self.pose = "jump"
            if self.y <= 0:
                self.y = 0
                self.set_state("idle")
                self.game.sfx("land")
            return
        if st == "held":
            self.update_held(dt)
            return
        if st == "hurt":
            if self.t >= 0.3:
                self.set_state("idle")
            return
        if st == "grab":
            self.update_grab(dt)
            return
        if st == "attack":
            self.update_attack(dt)
            return
        if st == "jump":
            self.update_jump(dt)
            return
        self.control(dt)
        if self.y <= 0 and self.game.in_water(self.x, self.z) and self.state in ("idle", "walk"):
            self.set_state("sink")
            self.drop_weapon()
            self.splash()

    def heavy(self):
        return self.weapon in ("crate", "barrel")

    def control(self, dt):
        p, g = self.pad, self.game
        dx, dz = p.axis()
        heavy = self.heavy()
        sp = self.speed * (0.72 if heavy else 1.0)
        punch, kick = p.pressed("punch"), p.pressed("kick")
        if punch and kick and not heavy and not self.weapon:
            self.start_attack("spin")
            return
        if p.pressed("jump") and not heavy:
            self.set_state("jump")
            self.vy = JUMP_V
            self.jvx = dx * sp * 1.2
            self.jvz = dz * sp * 0.45
            self.atk = None
            if dx:
                self.face = dx
            g.sfx("jump", 0.6)
            return
        if punch or kick:
            if heavy:
                self.start_attack("toss")
                return
            it = g.item_at(self)
            if punch and it is not None and not self.weapon:
                self.pick_up(it)
                return
            if self.weapon in ("bat", "pipe"):
                self.start_attack("swing")
                return
            if self.weapon == "knife":
                if punch:
                    self.start_attack("toss")
                else:
                    self.start_attack("stab")
                return
            if kick and g.enemy_behind_only(self):
                self.start_attack("elbow")
                return
            self.start_attack(self.next_chain("p" if punch else "k"))
            return
        moving = dx != 0 or dz != 0
        self.x += dx * sp * dt
        self.z += dz * sp * 0.62 * dt
        self.z = max(0.0, min(DEPTH, self.z))
        if dx:
            self.face = dx
        if moving:
            self.state = "walk"
            self.ph = (self.ph + dt * 1.7) % 1.0
        else:
            self.state = "idle"
            self.ph = (self.ph + dt * 0.8) % 1.0
        self.pose = ("cwalk" if moving else "lift") if heavy else ("walk" if moving else "idle")
        if dx and not self.weapon:
            e = g.grab_target(self, dx)
            if e is not None:
                self.start_grab(e)

    def next_chain(self, kind):
        chain = PUNCH_CHAIN if kind == "p" else KICK_CHAIN
        i = self.chain_i if (self.chain_t > 0 and self.chain_kind == kind) else 0
        return chain[min(i, len(chain) - 1)]

    def start_attack(self, name):
        self.set_state("attack")
        self.atk = name
        self.atk_hits = set()
        self.atk_fired = False
        self.atk_whiff = False

    def pick_up(self, it):
        g = self.game
        info = ITEMS[it.kind]
        it.remove = True
        if info["kind"] in ("melee", "throw", "heavy"):
            self.weapon = it.kind
            self.uses = it.uses if it.uses else info.get("uses", 0)
            g.sfx("pickup")
            if info["kind"] == "heavy":
                self.set_state("attack")
                self.atk = "lift"
                self.atk_hits = set()
        self.pose = "crouch"

    def update_attack(self, dt):
        g = self.game
        if self.atk == "lift":
            self.pose = "crouch" if self.t < 0.15 else "lift"
            if self.t > 0.3:
                self.set_state("idle")
            return
        if self.atk == "throwpose":
            self.pose = "throw"
            if self.t > 0.3:
                self.set_state("idle")
            return
        a = ATTACKS[self.atk]
        w, act, tot = a["t"]
        t = self.t
        if self.atk == "spin":
            self.pose = "spin" if w <= t < act else "crouch"
            self.ph = (t * 7) % 1.0
        elif t < w:
            self.pose = a["poses"][0]
        elif t < tot * 0.85:
            self.pose = a["poses"][1]
        else:
            self.pose = "idle"
        if self.atk == "toss":
            if t >= w and not self.atk_fired:
                self.atk_fired = True
                self.throw_item()
        elif a["rect"] and w <= t < act:
            if a.get("lunge"):
                self.x += self.face * a["lunge"] * dt
            dmg = a["dmg"] * self.power
            if self.atk == "swing":
                dmg = ITEMS[self.weapon]["dmg"] * self.power if self.weapon in ITEMS else dmg
            n = g.melee(self, a["rect"], dmg, a.get("kd", False), g.enemies, self.atk_hits, a.get("sfx", "punch"),
                        both=self.atk == "spin")
            if n:
                self.on_attack_hit()
            elif not self.atk_whiff:
                self.atk_whiff = True
                g.sfx("whoosh", 0.35)
        if t >= tot:
            self.set_state("idle")
            self.atk = None

    def on_attack_hit(self):
        name = self.atk
        for kind, chain in (("p", PUNCH_CHAIN), ("k", KICK_CHAIN)):
            if name in chain:
                i = chain.index(name) + 1
                self.chain_kind = kind
                self.chain_i = 0 if i >= len(chain) else i
                self.chain_t = 0.6
        if name == "spin":
            if not self.atk_fired:
                self.atk_fired = True
                self.hp = max(1, self.hp - ATTACKS["spin"]["cost"])
        if name == "swing" and self.weapon in ("bat", "pipe"):
            self.uses -= 1
            if self.uses <= 0:
                self.game.sfx("break")
                self.game.debris(self.x + self.face * 20, self.z, 30, self.weapon)
                self.weapon = None

    def throw_item(self):
        g = self.game
        kind = self.weapon
        if kind is None:
            return
        self.weapon = None
        if kind == "knife":
            it = Item(g, "knife", self.x + self.face * 10, self.z, y=32)
            it.state = "fly"
            it.vx = self.face * 260
            it.team = "p"
            it.owner = self
            g.sfx("knife")
        else:
            it = Item(g, kind, self.x + self.face * 6, self.z, y=50)
            it.state = "fly"
            it.vx = self.face * 200
            it.vy = 60
            it.team = "p"
            it.owner = self
            g.sfx("throw")
        g.items.append(it)

    def update_jump(self, dt):
        g, p = self.game, self.pad
        self.x += self.jvx * dt
        self.z = max(0.0, min(DEPTH, self.z + self.jvz * dt))
        self.vy -= GRAVITY * dt
        self.y += self.vy * dt
        if (p.pressed("punch") or p.pressed("kick")) and self.atk is None and self.y > 4:
            self.atk = "jkick"
            self.atk_hits = set()
            g.sfx("whoosh", 0.4)
        if self.atk == "jkick":
            a = ATTACKS["jkick"]
            if g.melee(self, a["rect"], a["dmg"] * self.power, True, g.enemies, self.atk_hits, a["sfx"]):
                pass
        self.pose = "jkick" if self.atk else "jump"
        if self.y <= 0:
            self.y = 0.0
            self.atk = None
            self.set_state("idle")
            g.sfx("land", 0.5)

    # --- grabbing enemies --------------------------------------------------
    def start_grab(self, e):
        self.set_state("grab")
        self.holding = e
        self.grab_n = 0
        self.knee_t = 0.0
        e.release_all()
        e.script = None
        e.set_state("grabbed")
        e.held_by = self
        e.face = -self.face
        self.game.sfx("grab")

    def update_grab(self, dt):
        e, p, g = self.holding, self.pad, self.game
        if e is None or e.state != "grabbed" or e.held_by is not self:
            self.holding = None
            self.set_state("idle")
            return
        e.x = self.x + self.face * 15 * max(1.0, e.scale)
        e.z = self.z
        e.pose = "held"
        self.knee_t = max(0.0, self.knee_t - dt)
        self.pose = "knee" if self.knee_t > 0.08 else "grab"
        dx, _ = p.axis()
        if p.pressed("punch") and self.knee_t <= 0:
            self.knee_t = 0.24
            self.grab_n += 1
            dmg = int(round(ATTACKS["knee"]["dmg"] * self.power))
            e.hp -= dmg
            e.flash = 0.08
            self.add_score(dmg * 10)
            self.last_enemy, self.last_enemy_t = e, 2.5
            g.sfx("punch")
            g.freeze(0.04)
            g.spark(e.x - self.face * 4, e.z, 24)
            if self.grab_n >= 3 or e.hp <= 0:
                self.holding = None
                e.held_by = None
                e.last_hitter = self
                e.knockdown(self.face, 1.0)
                e.vy = 210
                self.set_state("idle")
            return
        if p.pressed("kick") or p.pressed("jump"):
            self.holding = None
            e.held_by = None
            e.last_hitter = self
            dmg = int(round(9 * self.power))
            e.hp -= dmg
            self.add_score(dmg * 10)
            self.last_enemy, self.last_enemy_t = e, 2.5
            e.x = self.x - self.face * 4
            e.knockdown(-self.face, 2.0)
            e.vy = 240
            e.thrown_by = self
            e.thrown_hits = set()
            g.sfx("throw")
            self.set_state("attack")
            self.atk = "throwpose"
            return
        if (dx and dx != self.face) or self.t > 1.7:
            self.holding = None
            e.held_by = None
            e.set_state("hurt")
            self.set_state("idle")

    # --- being grabbed ------------------------------------------------------
    def update_held(self, dt):
        h, p = self.held_by, self.pad
        self.pose = "gripped"
        if h is None or h.state != "hold" or h.holding is not self:
            self.held_by = None
            self.set_state("idle")
            return
        dx, _ = p.axis()
        if dx and dx != self.last_dx:
            self.escape += 1
            self.game.sfx("shake", 0.4)
        self.last_dx = dx
        if p.pressed("punch") or p.pressed("kick") or p.pressed("jump"):
            self.escape += 0.5
        if self.escape >= 6:
            h.release_hold(stagger=True)
            self.held_by = None
            self.set_state("idle")
            self.invuln = 0.5

    # --- life -------------------------------------------------------------
    def on_dead(self):
        pass

    def lose_life(self):
        self.lives -= 1
        self.release_all()
        if self.lives > 0:
            self.respawn()
        else:
            self.out = True
            self.set_state("out")
            self.game.on_player_out(self)

    def respawn(self):
        g = self.game
        self.x = g.cam + (60 if self.idx == 0 else 100)
        self.z = DEPTH * 0.5
        self.y = 130
        self.vy = 0
        self.hp = self.maxhp
        self.weapon = None
        self.set_state("drop")
        self.invuln = 3.0

    def splash(self):
        self.game.splash(self.x, self.z)
        if self.state == "fall":
            self.set_state("sink")

    def draw(self, surf, cam):
        if self.out:
            return
        if self.state == "sink" and self.t > 0.1:
            return
        super().draw(surf, cam)


# ============================================================================
# Enemies and bosses
# ============================================================================
class Enemy(Fighter):
    def __init__(self, game, kind, x, z, face, hp_mul=1.0):
        e = ENEMIES[kind]
        super().__init__(game, e["char"], x, z, face)
        self.kind = kind
        self.e = e
        self.name = e["name"]
        self.boss = e.get("boss", False)
        tune = game.tune
        self.hp = self.maxhp = max(1, int(e["hp"] * tune["hp"] * hp_mul))
        self.speed = e["speed"]
        self.dmg_mul = tune["dmg"]
        self.weapon = e.get("weapon")
        self.moves = list(e["moves"])
        self.script = None
        self.si = 0
        self.st = 0.0
        self.step_hits = set()
        self.rehit_t = 0.0
        self.cool = random.uniform(0.8, 1.6)
        self.think = 0.0
        self.intent = "approach"
        self.off_z = 0.0
        self.hover_dx = 70.0
        self.entering = True
        self.enraged = False
        self.jvx = 0.0
        self.hold_t = 0.0
        self.hold_tick = 0.0
        self.counter = False

    def armored(self):
        if self.state == "hold":
            return False
        if self.script is not None:
            return bool(self.script[self.si][2].get("armor"))
        return False

    def take_hit(self, dmg, kd, dirx, src=None, sfx="punch"):
        g = self.game
        if self.boss and self.state in ("idle", "walk") and random.random() < self.e.get("block", 0) \
                and self.face == -dirx and self.hp > 0:
            self.set_state("block")
            self.pose = "block"
            g.sfx("block")
            g.spark(self.x - dirx * 8, self.z, 30, (160, 220, 255))
            self.cool = 0.0
            return
        if self.boss and self.combo_hits >= 3 and not kd:
            kd = True
        super().take_hit(dmg, kd, dirx, src, sfx)

    def on_dead(self):
        self.game.enemy_killed(self)

    # --- update ----------------------------------------------------------
    def update(self, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.combo_t = max(0.0, self.combo_t - dt)
        if self.combo_t <= 0:
            self.combo_hits = 0
        st = self.state
        if st in ("fall", "down", "getup"):
            self.update_fall(dt)
            return
        if st == "dead":
            self.pose = "lie"
            if self.t > 1.0:
                self.remove = True
            return
        if st == "grabbed":
            if self.held_by is None or self.held_by.holding is not self:
                self.held_by = None
                self.set_state("hurt")
            return
        if st == "hold":
            self.update_hold(dt)
            return
        if st == "hurt":
            if self.t >= 0.34:
                self.set_state("idle")
                self.cool = min(self.cool, random.uniform(0.15, 0.6))
            return
        if st == "block":
            if self.t >= 0.3:
                self.set_state("idle")
            return
        if self.boss and not self.enraged and self.hp < self.maxhp * 0.5:
            self.enraged = True
            self.speed *= 1.2
            self.start_script("summon" if self.e.get("summon") else "roar")
            return
        if self.script is not None:
            self.run_script(dt)
            return
        self.ai(dt)

    def ai(self, dt):
        g = self.game
        tgt = g.nearest_player(self)
        self.cool -= dt
        self.think -= dt
        if tgt is None:
            self.pose = "idle"
            self.ph = (self.ph + dt * 0.8) % 1.0
            return
        dx, dz = tgt.x - self.x, tgt.z - self.z
        adx = abs(dx)
        if adx > 3:
            self.face = 1 if dx > 0 else -1
        if self.think <= 0:
            self.think = random.uniform(0.5, 1.2)
            ranged = self.e.get("ranged")
            if ranged and random.random() < 0.7:
                self.intent = "range"
                self.hover_dx = random.uniform(*ranged)
            elif self.boss or random.random() < 0.65:
                self.intent = "approach"
            else:
                self.intent = "hover"
                self.hover_dx = random.uniform(55, 95)
            self.off_z = random.uniform(-1, 1)
        limit = g.tune["attackers"] + (1 if self.boss else 0)
        busy = g.attackers() >= limit and self.script is None
        intent = self.intent
        if busy and intent == "approach" and not self.boss:
            intent = "hover"
            self.hover_dx = max(self.hover_dx, 60)
        side = -1 if self.x < tgt.x else 1
        if intent == "approach":
            gx, gz = tgt.x + side * 18 * self.scale, tgt.z + self.off_z * 2
        elif intent == "range":
            gx, gz = tgt.x + side * self.hover_dx, tgt.z
        else:
            gx, gz = tgt.x + side * self.hover_dx, tgt.z + self.off_z * 16
        sp = self.speed
        mx, mz = gx - self.x, gz - self.z
        moved = False
        if abs(mx) > 3:
            self.x += math.copysign(min(abs(mx), sp * dt), mx)
            moved = True
        if abs(mz) > 1.5:
            self.z += math.copysign(min(abs(mz), sp * 0.6 * dt), mz)
            moved = True
        for o in g.enemies:
            if o is not self and o.state in ("idle", "walk") and abs(o.x - self.x) < 12 and abs(o.z - self.z) < 6:
                self.z += (2 if self.z >= o.z else -2) * dt * 20
        self.z = g.safe_z(self.x, max(0.0, min(DEPTH, self.z)))
        self.state = "walk" if moved else "idle"
        self.pose = "walk" if moved else "idle"
        self.ph = (self.ph + dt * (1.4 if moved else 0.8)) % 1.0
        if self.entering or self.cool > 0 or tgt.state in ("dead", "drop", "sink"):
            return
        if abs(dz) > 6:
            return
        cands = [m for m in self.moves if m[2] <= adx <= m[3] * max(1.0, self.scale * 0.9)]
        if not cands:
            return
        if busy and not self.boss:
            cands = [m for m in cands if m[0] in ("throwknife",)]
            if not cands:
                return
        tot = sum(m[1] for m in cands)
        r = random.uniform(0, tot)
        for m in cands:
            r -= m[1]
            if r <= 0:
                self.start_script(m[0])
                break

    # --- scripts ----------------------------------------------------------
    def start_script(self, name):
        self.script = MOVES[name]
        self.script_name = name
        self.si = 0
        self.state = "attack"
        tgt = self.game.nearest_player(self)
        if tgt is not None and abs(tgt.x - self.x) > 2:
            self.face = 1 if tgt.x > self.x else -1
        self.enter_step()

    def enter_step(self):
        g = self.game
        pose, dur, o = self.script[self.si]
        self.st = 0.0
        self.step_hits = set()
        self.rehit_t = 0.0
        self.pose = pose
        if "sfx" in o:
            g.sfx(o["sfx"])
        if "hit" in o:
            g.sfx("whoosh", 0.35)
        if "jump" in o:
            self.vy = o["jump"]
            self.y = 0.1
            if o.get("seek"):
                tgt = g.nearest_player(self)
                T = 2 * o["jump"] / GRAVITY
                if tgt is not None:
                    self.jvx = max(-240.0, min(240.0, (tgt.x - self.x) / T))
                    self.face = 1 if tgt.x >= self.x else -1
                else:
                    self.jvx = 0.0
            else:
                self.jvx = self.face * o.get("v", 0)
        if o.get("quake"):
            g.shake(0.4, 4)
            g.sfx("boom")
            g.quake(self, 80 * self.scale, int(6 * self.dmg_mul))
        if "spawn" in o:
            self.spawn(o["spawn"])
        if "summon" in o:
            for k in range(o["summon"]):
                g.spawn_enemy(self.e.get("summon", "punk"), "L" if k % 2 == 0 else "R")

    def spawn(self, kind):
        g = self.game
        h = 34 * self.scale
        if kind == "eknife":
            g.items.append(Item.projectile(g, "eknife", self, h, 0.0, 6))
        elif kind == "fan":
            for vz in (-28.0, 0.0, 28.0):
                g.items.append(Item.projectile(g, "eknife", self, h, vz, 5))
        elif kind == "stars":
            for vz in (-34.0, -10.0, 14.0):
                g.items.append(Item.projectile(g, "star", self, h, vz, 6))
        g.sfx("knife")

    def run_script(self, dt):
        g = self.game
        pose, dur, o = self.script[self.si]
        self.st += dt
        self.pose = pose
        if "anim" in o:
            self.ph = (self.ph + dt * o["anim"]) % 1.0
        air = "jump" in o
        if air:
            self.x += self.jvx * dt
            self.vy -= GRAVITY * dt
            self.y += self.vy * dt
        elif "v" in o:
            self.x += self.face * o["v"] * dt
        if "track" in o:
            tgt = g.nearest_player(self)
            if tgt is not None:
                d = tgt.z - self.z
                self.z += math.copysign(min(abs(d), o["track"] * dt), d)
                dxx = tgt.x - self.x
                self.x += math.copysign(min(abs(dxx), o["track"] * dt), dxx)
        self.z = g.safe_z(self.x, max(0.0, min(DEPTH, self.z)))
        if "hit" in o:
            h = o["hit"]
            if o.get("rehit"):
                self.rehit_t += dt
                if self.rehit_t >= o["rehit"]:
                    self.rehit_t = 0.0
                    self.step_hits = set()
            if not air or self.vy < 60:
                g.melee(self, h["rect"], h["dmg"] * self.dmg_mul, h["kd"], g.live_players(), self.step_hits,
                        h["sfx"], both=h.get("both", False))
        if "grab" in o and self.holding is None:
            p = g.try_enemy_grab(self, o["grab"])
            if p is not None:
                self.script = None
                self.set_state("hold")
                self.holding = p
                p.release_all()
                p.atk = None
                p.set_state("held")
                p.held_by = self
                p.escape = 0.0
                p.face = -self.face
                self.hold_tick = 0.0
                g.sfx("grab")
                return
        done = (air and self.y <= 0 and self.st > 0.05) or (not air and self.st >= dur) or self.st > 3.0
        if air and self.y <= 0:
            self.y = 0.0
            self.vy = 0.0
        if done:
            if air:
                g.sfx("land", 0.6)
                g.dust(self.x, self.z)
            self.si += 1
            if self.si >= len(self.script):
                self.script = None
                self.set_state("idle")
                c = random.uniform(0.35, 0.9) if self.boss else random.uniform(0.6, 1.5)
                self.cool = c * g.tune["cool"] * (0.65 if self.enraged else 1.0)
            else:
                self.enter_step()

    # --- holding a player ---------------------------------------------------
    def update_hold(self, dt):
        g = self.game
        p = self.holding
        if p is None or p.held_by is not self or p.state != "held":
            self.holding = None
            self.set_state("idle")
            return
        p.x = self.x + self.face * 14 * self.scale
        p.z = self.z
        self.hold_tick += dt
        self.pose = "headbutt" if 0.4 < self.hold_tick < 0.55 else "grab"
        if self.hold_tick >= 0.55:
            self.hold_tick = 0.0
            p.hp -= max(1, int(3 * self.dmg_mul))
            p.flash = 0.08
            g.sfx("punch")
            g.spark(p.x, p.z, 34)
            if p.hp <= 0:
                self.release_hold()
                p.knockdown(self.face, 1.2)
                return
        if self.t > 2.0:
            self.release_hold()
            p.hp -= max(1, int(5 * self.dmg_mul))
            p.x = self.x - self.face * 4
            p.knockdown(-self.face, 1.6)
            g.sfx("throw")
            self.cool = 1.0

    def release_hold(self, stagger=False):
        p = self.holding
        self.holding = None
        if p is not None and p.held_by is self:
            p.held_by = None
            if p.state == "held":
                p.set_state("idle")
        if stagger:
            self.set_state("hurt")
            self.t = -0.4
            self.pose = "hurt"
        else:
            self.set_state("idle")

    def update_entering(self, cam):
        if self.entering and cam + 6 < self.x < cam + W - 6:
            self.entering = False


# ============================================================================
# Items, weapons and projectiles
# ============================================================================
class Item:
    def __init__(self, game, kind, x, z, y=0.0):
        self.game = game
        self.kind = kind
        self.x, self.z, self.y = float(x), float(z), float(y)
        self.vx = self.vy = self.vz = 0.0
        self.state = "ground"
        self.team = None
        self.owner = None
        self.dmg = ITEMS.get(kind, {}).get("dmg", 6)
        self.hits = set()
        self.t = 0.0
        self.remove = False
        self.uses = None
        self.contents = None
        if kind == "crate":
            self.contents = random.choice(("chicken", "soda", "cash", None))

    @classmethod
    def projectile(cls, game, kind, owner, h, vz, dmg):
        it = cls(game, kind, owner.x + owner.face * 10, owner.z, y=h)
        it.state = "fly"
        it.team = "e"
        it.owner = owner
        it.vx = owner.face * (210 if kind == "eknife" else 190)
        it.vz = vz
        it.dmg = max(1, int(dmg * owner.dmg_mul))
        return it

    def update(self, dt):
        g = self.game
        self.t += dt
        if self.state == "ground":
            if self.y > 0 or self.vy > 0:
                self.vy -= GRAVITY * dt
                self.y += self.vy * dt
                self.x += self.vx * dt
                if self.y <= 0:
                    self.y = 0.0
                    self.vy = 0.0
                    self.vx = 0.0
                    if g.in_water(self.x, self.z):
                        g.splash(self.x, self.z)
                        self.remove = True
            return
        targets = g.enemies if self.team == "p" else g.live_players()
        if self.state == "fly":
            self.x += self.vx * dt
            self.z += self.vz * dt
            if self.kind in ("crate", "barrel"):
                self.vy -= GRAVITY * 0.7 * dt
                self.y += self.vy * dt
            for f in targets:
                if f in self.hits or not f.can_be_hit():
                    continue
                if f.body_overlap(self.x - 7, self.x + 7, self.y - 6, self.y + 6, self.z, 8):
                    self.hits.add(f)
                    heavy = self.kind in ("crate", "barrel")
                    kd = heavy or self.kind == "knife"
                    f.take_hit(self.dmg, kd, 1 if self.vx > 0 else -1, self.owner if self.team == "p" else None,
                               "hit" if heavy else "slash")
                    if self.kind != "barrel":
                        self.shatter()
                        return
            if self.kind in ("crate", "barrel") and self.y <= 0:
                self.y = 0.0
                if g.in_water(self.x, self.z):
                    g.splash(self.x, self.z)
                    self.remove = True
                elif self.kind == "barrel":
                    self.state = "roll"
                    self.t = 0.0
                    self.vx *= 0.8
                    g.sfx("thud", 0.6)
                else:
                    self.shatter()
            if self.x < g.cam - 40 or self.x > g.cam + W + 40:
                self.remove = True
        elif self.state == "roll":
            self.x += self.vx * dt
            self.vx *= (1 - 0.6 * dt)
            for f in targets:
                if f not in self.hits and f.can_be_hit() and f.body_overlap(self.x - 8, self.x + 8, 0, 14, self.z, 8):
                    self.hits.add(f)
                    f.take_hit(self.dmg, True, 1 if self.vx > 0 else -1, self.owner, "hit")
            if self.t > 1.1 or self.x < g.cam - 30 or self.x > g.cam + W + 30:
                self.shatter()

    def shatter(self):
        g = self.game
        self.remove = True
        if self.kind in ("crate", "barrel"):
            g.sfx("break")
            g.debris(self.x, self.z, max(4, self.y), "plank")
            if self.contents:
                it = Item(g, self.contents, self.x, self.z, y=10)
                it.vy = 100
                g.items.append(it)
        elif self.kind == "knife" and self.team == "p":
            pass
        else:
            g.spark(self.x, self.z, self.y, (200, 220, 255))

    def draw_shadow(self, surf, cam):
        img = gfx.soft_ellipse(14, 4, (0, 0, 0), 80)
        surf.blit(img, (int(self.x - cam - 7), int(FLOOR_Y + self.z - 2)))

    def draw(self, surf, cam):
        k = self.kind
        if k == "star":
            img = gfx.prop("star", int(self.t * 16) % 4)
        else:
            img = gfx.prop(k)
        if self.state in ("fly", "roll") and self.vx < 0:
            img = pygame.transform.flip(img, True, False)
        if self.state == "roll":
            img = pygame.transform.rotate(img, (self.t * 600) % 360)
        if self.state == "ground" and ITEMS.get(k, {}).get("kind") in ("food", "cash"):
            if int(self.t * 4) % 6 == 0:
                img = gfx.white(img)
        sx = int(self.x - cam - img.get_width() / 2)
        sy = int(FLOOR_Y + self.z - self.y - img.get_height())
        surf.blit(img, (sx, sy))


class Vent:
    """Floor steam vent. Cycles: idle -> hiss warning -> scalding blast that hits anyone on top of it."""
    PERIOD = 3.2

    def __init__(self, game, x, z, phase):
        self.game = game
        self.x, self.z = x, z
        self.t = phase
        self.hits = set()

    def state(self):
        c = self.t % self.PERIOD
        if c < 1.6:
            return 0
        if c < 2.2:
            return 1
        return 2

    def update(self, dt):
        g = self.game
        before = self.state()
        self.t += dt
        s = self.state()
        if s == 2 and before != 2:
            self.hits = set()
            if g.cam - 20 < self.x < g.cam + W + 20:
                g.sfx("steam", 0.7)
        if s == 1 and int(self.t * 10) % 3 == 0:
            g.puff(self.x + random.uniform(-6, 6), self.z, 2, small=True)
        if s == 2:
            g.puff(self.x + random.uniform(-8, 8), self.z, random.uniform(0, 10))
            for f in g.live_players() + g.enemies:
                if f not in self.hits and f.can_be_hit() and f.y < 14 and abs(f.x - self.x) < 13 \
                        and abs(f.z - self.z) < 8:
                    self.hits.add(f)
                    f.take_hit(7, True, 1 if f.x >= self.x else -1, None, "hurt")
