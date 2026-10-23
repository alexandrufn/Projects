"""Title, controls, story, stage clear, continue and ending screens."""
import pygame

import gfx
from config import W, H, FLOOR_Y, CHARS, STAGES, DIFFICULTIES, START_LIVES

STORY = [
    "NEON CITY, 1991.",
    "THE IRON SERPENTS RUN EVERY STREET BETWEEN THE DOCKS AND THE TOWER.",
    "LAST NIGHT THEY TOOK TOMO, VERA'S KID BROTHER, TO MAKE HER CLOSE HER GYM.",
    "VERA CALLED THE ONE PERSON CRAZY ENOUGH TO HELP: HER OLD SPARRING PARTNER KAI.",
    "NO POLICE. NO DEALS. JUST FOUR STREETS OF TROUBLE BETWEEN THEM AND TOMO.",
]


def draw_char(surf, ckey, pose, pos, face=1, scale=2, ph=0.0, weapon=None):
    img, (ax, ay) = gfx.frame(ckey, CHARS[ckey], pose, ph, face < 0, weapon)
    if scale != 1:
        img = pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))
        ax, ay = ax * scale, ay * scale
    surf.blit(img, (pos[0] - ax, pos[1] - ay))


class Scene:
    def __init__(self, app):
        self.app = app
        self.t = 0.0

    def handle(self, events):
        pass

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        pass


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = gfx.Background("neon", 4000)
        self.sel = 0
        self.stage = 0
        app.audio.music("title")
        app.controls.shared = True

    def items(self):
        reached = self.app.save.get("reached", 0)
        out = ["1 PLAYER", "2 PLAYERS"]
        if reached > 0:
            out.append("STAGE  < %d >" % (self.stage + 1))
        out += ["DIFFICULTY  < %s >" % DIFFICULTIES[self.app.save.get("diff", 1)], "CONTROLS", "QUIT"]
        return out

    def handle(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.app.quit()

    def update(self, dt):
        super().update(dt)
        c, app = self.app.controls, self.app
        items = self.items()
        if c.menu_pressed("up"):
            self.sel = (self.sel - 1) % len(items)
            app.audio.play("blip")
        if c.menu_pressed("down"):
            self.sel = (self.sel + 1) % len(items)
            app.audio.play("blip")
        label = items[self.sel]
        lr = (1 if c.menu_pressed("right") else 0) - (1 if c.menu_pressed("left") else 0)
        if lr and label.startswith("STAGE"):
            self.stage = (self.stage + lr) % (app.save.get("reached", 0) + 1)
            app.audio.play("blip")
        if lr and label.startswith("DIFF"):
            app.save["diff"] = (app.save.get("diff", 1) + lr) % len(DIFFICULTIES)
            app.write_save()
            app.audio.play("blip")
        if c.confirm():
            app.audio.play("select")
            if label in ("1 PLAYER", "2 PLAYERS"):
                roster = [dict(idx=0, lives=START_LIVES, score=0)]
                if label == "2 PLAYERS":
                    roster.append(dict(idx=1, lives=START_LIVES, score=0))
                if self.stage == 0:
                    app.change(StoryScene(app, roster))
                else:
                    from game import GameScene
                    app.change(GameScene(app, self.stage, roster))
            elif label == "CONTROLS":
                app.change(ControlsScene(app))
            elif label == "QUIT":
                app.quit()

    def draw(self, surf):
        self.bg.draw(surf, self.t * 18, self.t)
        surf.fill((8, 6, 14), (0, 0, W, 30))
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((10, 4, 20, 110))
        surf.blit(veil, (0, 0))
        draw_char(surf, "kai", "idle", (54, FLOOR_Y + 46), 1, 2, self.t * 0.8)
        draw_char(surf, "vera", "idle", (268, FLOOR_Y + 46), -1, 2, self.t * 0.8 + 0.5)
        a = gfx.fancy_text("NEON", 40, (120, 250, 255), (230, 60, 200), thick=3)
        b = gfx.fancy_text("KNUCKLES", 40, (255, 240, 140), (240, 80, 40), thick=3)
        surf.blit(a, a.get_rect(center=(W // 2, 46)))
        surf.blit(b, b.get_rect(center=(W // 2, 76)))
        gfx.text(surf, "A 16-BIT STREET BRAWLER", 7, (W // 2, 98), (220, 200, 255), outline=True)
        for i, s in enumerate(self.items()):
            on = i == self.sel
            col = (255, 255, 255) if on else (170, 150, 200)
            gfx.text(surf, ("> " + s + " <") if on else s, 7, (W // 2, 118 + i * 12), col, outline=True)
        gfx.text(surf, "HI %07d" % self.app.save.get("hi", 0), 7, (W // 2, H - 12), (255, 220, 120), outline=True)
        gfx.text(surf, "F11 FULLSCREEN", 7, (W - 4, H - 12), (130, 120, 160), anchor="topright", outline=True)


class ControlsScene(Scene):
    ROWS = [
        ("", "PLAYER 1", "PLAYER 2"),
        ("MOVE", "W A S D", "ARROWS"),
        ("PUNCH", "J  OR F", "Z  , OR NUM1"),
        ("KICK", "K  OR G", "X  . OR NUM2"),
        ("JUMP", "L  SPACE OR H", "C  / OR NUM3"),
        ("START / JOIN", "ENTER", "RIGHT SHIFT"),
    ]
    MOVES = [
        "PUNCH X3: JAB, CROSS, UPPERCUT.  KICK X2: KICK, ROUNDHOUSE.",
        "KICK WITH AN ENEMY ONLY BEHIND YOU: BACK ELBOW.",
        "PUNCH + KICK: SPIN KICK. HITS ALL AROUND, COSTS HEALTH.",
        "JUMP, THEN PUNCH OR KICK: FLYING KICK.",
        "WALK INTO A STAGGERED ENEMY TO GRAB. PUNCH = KNEE, KICK = THROW.",
        "PUNCH ON A WEAPON TO PICK IT UP. KNIVES AND CRATES ARE THROWN.",
        "GRABBED? WIGGLE LEFT AND RIGHT TO BREAK FREE.",
        "GAMEPADS: A JUMP, X PUNCH, B / Y KICK, START.",
    ]

    def update(self, dt):
        super().update(dt)
        c = self.app.controls
        if c.confirm() or c.menu_pressed("kick"):
            self.app.audio.play("select")
            self.app.change(TitleScene(self.app))

    def handle(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.app.change(TitleScene(self.app))

    def draw(self, surf):
        gfx.dither_fill(surf, surf.get_rect(), (20, 10, 40), (60, 20, 70), steps=8)
        gfx.text(surf, "CONTROLS", 20, (W // 2, 16), (255, 230, 120), outline=True)
        for i, (a, b, c) in enumerate(self.ROWS):
            y = 32 + i * 10
            col = (255, 255, 255) if i else (255, 170, 120)
            gfx.text(surf, a, 7, (60, y), (200, 190, 255), anchor="topleft", outline=True)
            gfx.text(surf, b, 7, (150, y), col, anchor="topleft", outline=True)
            gfx.text(surf, c, 7, (232, y), col, anchor="topleft", outline=True)
        y = 98
        for m in self.MOVES:
            for line in gfx.wrap(m, 7, W - 20):
                gfx.text(surf, line, 7, (10, y), (230, 230, 240), anchor="topleft", outline=True)
                y += 9
            y += 2
        gfx.text(surf, "PRESS PUNCH TO GO BACK", 7, (W // 2, H - 8), (255, 220, 120), outline=True)


class StoryScene(Scene):
    def __init__(self, app, roster):
        super().__init__(app)
        self.roster = roster
        self.bg = gfx.Background("neon", 4000)

    def update(self, dt):
        super().update(dt)
        if self.app.controls.confirm() and self.t > 0.3:
            from game import GameScene
            self.app.audio.play("select")
            self.app.change(GameScene(self.app, 0, self.roster))

    def draw(self, surf):
        self.bg.draw(surf, 200 + self.t * 6, self.t)
        surf.fill((8, 6, 14), (0, 0, W, 30))
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 170))
        surf.blit(veil, (0, 0))
        chars = int(self.t * 40)
        y = 30
        for line in STORY:
            for w in gfx.wrap(line, 7, W - 40):
                shown = w[:max(0, chars)]
                chars -= len(w)
                gfx.text(surf, shown, 7, (20, y), (240, 236, 255), anchor="topleft", outline=True)
                y += 11
            y += 7
        draw_char(surf, "vera", "idle", (140, H - 14), 1, 1, self.t)
        draw_char(surf, "kai", "idle", (180, H - 14), -1, 1, self.t + 0.3)
        if int(self.t * 2) % 2:
            gfx.text(surf, "PRESS PUNCH", 7, (W // 2, H - 8), (255, 220, 120), outline=True)


class StageClearScene(Scene):
    def __init__(self, app, si, roster, time_left, players):
        super().__init__(app)
        self.si = si
        self.roster = roster
        self.time_bonus = time_left * 50
        self.hp = {p.idx: p.hp for p in players}
        self.lines = []
        for r in roster:
            hb = self.hp.get(r["idx"], 0) * 40
            r["score"] += self.time_bonus + hb
            self.lines.append((("KAI", "VERA")[r["idx"]], hb, r["score"]))
        app.update_hi(max(r["score"] for r in roster) if roster else 0, si + 1)
        app.audio.music(None)

    def update(self, dt):
        super().update(dt)
        if self.t > 1.0 and (self.app.controls.confirm() or self.t > 6):
            self.app.audio.play("select")
            if self.si + 1 < len(STAGES):
                from game import GameScene
                self.app.change(GameScene(self.app, self.si + 1, self.roster))
            else:
                self.app.change(EndingScene(self.app, self.roster))

    def draw(self, surf):
        gfx.dither_fill(surf, surf.get_rect(), (16, 8, 36), (70, 20, 60), steps=8)
        img = gfx.fancy_text("STAGE %d CLEAR" % (self.si + 1), 28, (255, 250, 180), (250, 140, 40))
        surf.blit(img, img.get_rect(center=(W // 2, 40)))
        gfx.text(surf, STAGES[self.si]["name"], 13, (W // 2, 62), (255, 255, 255), outline=True)
        gfx.text(surf, "TIME BONUS   %d" % self.time_bonus, 7, (W // 2, 88), (200, 220, 255), outline=True)
        for i, (name, hb, total) in enumerate(self.lines):
            if self.t > 0.6 + i * 0.5:
                y = 110 + i * 30
                gfx.text(surf, "%s   HEALTH BONUS %d" % (name, hb), 7, (W // 2, y), (255, 230, 160), outline=True)
                gfx.text(surf, "SCORE %07d" % total, 7, (W // 2, y + 11), (255, 255, 255), outline=True)
        if self.si + 1 < len(STAGES):
            gfx.text(surf, "NEXT: " + STAGES[self.si + 1]["name"], 7, (W // 2, H - 26), (190, 170, 255), outline=True)
        if self.t > 1.0 and int(self.t * 2) % 2:
            gfx.text(surf, "PRESS PUNCH", 7, (W // 2, H - 12), (255, 220, 120), outline=True)


class ContinueScene(Scene):
    def __init__(self, app, game):
        super().__init__(app)
        self.game = game
        self.count = 9.99
        app.update_hi(max((p.score for p in game.players if p), default=0), game.si)

    def update(self, dt):
        super().update(dt)
        c = self.app.controls
        before = int(self.count)
        self.count -= dt
        if int(self.count) != before and self.count > 0:
            self.app.audio.play("blip")
        if self.t > 0.5 and any(p.pressed("start") for p in c.pads):
            self.app.audio.play("coin")
            self.game.revive_all()
            self.app.change(self.game)
            return
        if self.t > 0.5 and (c.menu_pressed("punch") or c.menu_pressed("kick")):
            self.count -= 1.0
        if self.count <= 0:
            self.app.change(TitleScene(self.app))

    def draw(self, surf):
        self.game.draw(surf)
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 180))
        surf.blit(veil, (0, 0))
        gfx.text(surf, "CONTINUE?", 20, (W // 2, 70), (255, 230, 120), outline=True)
        img = gfx.fancy_text(str(max(0, int(self.count))), 48, (255, 255, 255), (240, 80, 80), thick=3)
        surf.blit(img, img.get_rect(center=(W // 2, 112)))
        gfx.text(surf, "PRESS START (ENTER) TO KEEP FIGHTING", 7, (W // 2, 150), (240, 240, 255), outline=True)
        gfx.text(surf, "YOU KEEP YOUR PLACE, YOUR SCORE RESETS", 7, (W // 2, 162), (170, 160, 200), outline=True)


class EndingScene(Scene):
    TEXT = [
        "THE IRON SERPENTS ARE FINISHED.",
        "TOMO IS SAFE, AND VERA'S GYM OPENS AGAIN ON MONDAY.",
        "KAI SAYS HE IS ONLY STAYING FOR ONE CLASS.",
        "HE IS STILL THERE A YEAR LATER.",
    ]

    def __init__(self, app, roster):
        super().__init__(app)
        self.roster = roster
        self.bg = gfx.Background("tower", 4000)
        app.audio.music("title")
        app.update_hi(max((r["score"] for r in roster), default=0), len(STAGES) - 1)

    def update(self, dt):
        super().update(dt)
        if self.t > 3 and self.app.controls.confirm():
            self.app.change(TitleScene(self.app))

    def draw(self, surf):
        self.bg.draw(surf, 1200 + self.t * 4, self.t)
        surf.fill((8, 6, 14), (0, 0, W, 30))
        draw_char(surf, "kai", "victory", (110, FLOOR_Y + 40), 1, 1)
        draw_char(surf, "tomo", "cheer", (160, FLOOR_Y + 40), 1, 1, self.t)
        draw_char(surf, "vera", "pump", (210, FLOOR_Y + 40), -1, 1)
        img = gfx.fancy_text("THE END", 30, (255, 250, 180), (250, 120, 60))
        surf.blit(img, img.get_rect(center=(W // 2, 18)))
        veil = pygame.Surface((W - 20, 70), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        surf.blit(veil, (10, 36))
        for i, line in enumerate(self.TEXT):
            if self.t > 0.8 * i:
                gfx.text(surf, line, 7, (W // 2, 46 + i * 14), (240, 236, 255), outline=True)
        for i, r in enumerate(self.roster):
            gfx.text(surf, "%s  %07d" % (("KAI", "VERA")[r["idx"]], r["score"]), 7, (W // 2, H - 26 + i * 10),
                     (255, 230, 140), outline=True)
