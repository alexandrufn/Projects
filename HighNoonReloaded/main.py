"""High Noon: Reloaded - a 16-bit style remake of the classic ZX Spectrum western duel.

Run:  python main.py
"""
import json
import os
import sys

import pygame

from config import W, H, FPS, TITLE, SAVE_DIR, SAVE_FILE, SHERIFF


def load_save():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data.setdefault("unlocked", 1)
    data.setdefault("bounty", 0)
    data.setdefault("beaten", [])
    return data


class App:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        import gfx
        icon = gfx.build_character(SHERIFF)["head"][0]
        pygame.display.set_icon(pygame.transform.scale(icon, (40, 24)))
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self._loading()

        from audio import Audio
        self.audio = Audio()
        self.save = load_save()
        self.joysticks = []
        self.running = True

        from scenes import TitleScene
        self.scene = TitleScene(self)

    def _loading(self):
        import gfx
        self.screen.fill((20, 10, 6))
        gfx.text(self.screen, "SADDLING UP...", 16, (W // 2, H // 2), (255, 220, 120))
        pygame.display.flip()
        pygame.event.pump()

    # ------------------------------------------------------------- services
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

    def joy_index(self, instance_id):
        for i, j in enumerate(self.joysticks):
            if j.get_instance_id() == instance_id:
                return i
        return -1

    # ------------------------------------------------------------ main loop
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


def main():
    App().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
