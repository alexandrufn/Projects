"""Iron Fist: Temple of the Dragon - a 16-bit style kung-fu tower brawler.

Run:  python main.py            (options: --floor N  --diff 0|1|2)
"""
import json
import os
import sys

import pygame

from config import W, H, FPS, TITLE, SAVE_DIR, SAVE_FILE, FLOORS


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
        self.screen.fill((20, 8, 10))
        gfx.text(self.screen, "SHARPENING THE BLADES...", 14, (W // 2, H // 2), (238, 190, 84))
        pygame.display.flip()
        pygame.event.pump()
        pygame.display.set_icon(pygame.transform.scale(self._icon(), (32, 32)))
        from audio import Audio
        self.audio = Audio()
        self.save = load_save()
        self.joysticks = []
        self.running = True
        from scenes import TitleScene
        self.scene = TitleScene(self)

    def _icon(self):
        import gfx
        from config import CHARS
        img, _ = gfx.frame("hero", CHARS["hero"], "idle", 0.0, False)
        return img.subsurface(pygame.Rect(img.get_width() // 2 - 12, 2, 24, 24)).copy()

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

    def update_hi(self, score, floor):
        changed = False
        if score > self.save.get("hi", 0):
            self.save["hi"] = int(score)
            changed = True
        if floor > self.save.get("reached", 0):
            self.save["reached"] = min(len(FLOORS) - 1, floor)
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
            self.scene.handle(events)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()


def main(argv):
    app = App()
    floor = diff = None
    for i, a in enumerate(argv):
        if a == "--floor" and i + 1 < len(argv):
            floor = int(argv[i + 1]) - 1
        if a == "--diff" and i + 1 < len(argv):
            diff = int(argv[i + 1])
    if diff is not None:
        app.save["diff"] = diff
    if floor is not None:
        from scenes import IntroScene
        from config import START_LIVES
        app.scene = IntroScene(app, max(0, min(len(FLOORS) - 1, floor)), START_LIVES, 0)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
