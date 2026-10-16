"""Outlaw Gulch - a vertical-scrolling western shooter in the spirit of Capcom's Gun.Smoke.

Written from scratch with pygame; all graphics and sounds are generated in code.

Run:  python main.py
"""
import json
import os

import pygame

from config import W, H, FPS, TITLE, SAVE_DIR, SAVE_FILE
from inputs import Input


def load_save():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    if not isinstance(data.get("hi"), int):
        data["hi"] = 0
    return data


class App:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        import gfx
        from audio import Audio
        self.sprites = gfx.Sprites()
        pygame.display.set_icon(self.sprites.hero["hank"][(0, 0)])
        self.audio = Audio()
        self.save = load_save()
        self.input = Input()
        self.running = True
        from scenes import TitleScene
        self.scene = TitleScene(self)

    def change(self, scene):
        self.scene = scene

    def record_score(self, score):
        if score > self.save["hi"]:
            self.save["hi"] = score
            try:
                os.makedirs(SAVE_DIR, exist_ok=True)
                with open(SAVE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.save, f)
            except OSError:
                pass

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 20)
            events = pygame.event.get()
            if any(e.type == pygame.QUIT for e in events):
                break
            self.scene.update(dt, self.input.poll(events))
            self.scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()


if __name__ == "__main__":
    App().run()
