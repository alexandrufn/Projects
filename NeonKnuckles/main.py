"""Neon Knuckles - a 16-bit style co-op street brawler.

Run:  python main.py            (options: --stage N  --diff 0|1|2  --players 1|2)
"""
import json
import os
import sys

import pygame

from config import W, H, FPS, TITLE, SAVE_DIR, SAVE_FILE, STAGES, START_LIVES


def load_save():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data.setdefault("hi", 0)
    data.setdefault("reached", 0)
    data.setdefault("diff", 1)
    return data


class App:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        import gfx
        self.screen.fill((14, 6, 24))
        gfx.text(self.screen, "TUNING THE NEON...", 13, (W // 2, H // 2), (120, 250, 255))
        pygame.display.flip()
        pygame.event.pump()
        pygame.display.set_icon(pygame.transform.scale(self._icon(), (32, 32)))
        from audio import Audio
        from inputs import Controls
        self.audio = Audio()
        self.controls = Controls()
        self.save = load_save()
        self.joysticks = []
        self.running = True
        from scenes import TitleScene
        self.scene = TitleScene(self)

    def _icon(self):
        import gfx
        from config import CHARS
        img, (ax, ay) = gfx.frame("kai", CHARS["kai"], "idle", 0.0, False)
        return img.subsurface(pygame.Rect(ax - 12, ay - 54, 24, 24)).copy()

    def change(self, scene):
        self.scene = scene

    def quit(self):
        self.running = False

    def write_save(self):
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.save, f)
        except OSError:
            pass

    def update_hi(self, score, stage):
        changed = False
        if score > self.save.get("hi", 0):
            self.save["hi"] = int(score)
            changed = True
        if stage > self.save.get("reached", 0):
            self.save["reached"] = min(len(STAGES) - 1, stage)
            changed = True
        if changed:
            self.write_save()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            events = pygame.event.get()
            for e in events:
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and (e.key == pygame.K_F11 or
                                                   (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT)):
                    pygame.display.toggle_fullscreen()
                elif e.type == pygame.JOYDEVICEADDED:
                    self.joysticks.append(pygame.joystick.Joystick(e.device_index))
                elif e.type == pygame.JOYDEVICEREMOVED:
                    self.joysticks = [j for j in self.joysticks if j.get_instance_id() != e.instance_id]
            self.controls.update(events, self.joysticks)
            self.scene.handle(events)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()


def main(argv):
    app = App()
    stage = diff = None
    players = 1
    for i, a in enumerate(argv):
        if a == "--stage" and i + 1 < len(argv):
            stage = int(argv[i + 1]) - 1
        if a == "--diff" and i + 1 < len(argv):
            diff = int(argv[i + 1])
        if a == "--players" and i + 1 < len(argv):
            players = 2 if argv[i + 1] == "2" else 1
    if diff is not None:
        app.save["diff"] = max(0, min(2, diff))
    if stage is not None:
        from game import GameScene
        roster = [dict(idx=i, lives=START_LIVES, score=0) for i in range(players)]
        app.scene = GameScene(app, max(0, min(len(STAGES) - 1, stage)), roster)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
