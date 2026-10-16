"""Tiny synthesised sound effects (no audio files)."""
import array
import random

import pygame

RATE = 22050


def _make(parts, vol=0.25, wave="square"):
    buf = array.array("h")
    for f0, f1, dur in parts:
        n = max(1, int(RATE * dur))
        phase = 0.0
        last = 0.0
        for i in range(n):
            t = i / n
            f = f0 + (f1 - f0) * t
            phase += f / RATE
            if f <= 0:
                v = 0.0
            elif wave == "noise":
                # low-passed noise: a bigger f means a brighter crack, a smaller f a rumble
                last += (random.uniform(-1, 1) - last) * min(1.0, f / 4000.0)
                v = last * 2.2
            elif wave == "tri":
                v = 4 * abs((phase % 1) - 0.5) - 1
            else:
                v = 1.0 if (phase % 1) < 0.5 else -1.0
            buf.append(int(max(-1.0, min(1.0, v)) * ((1 - t) ** 0.7) * vol * 32767))
    return buf


class Audio:
    def __init__(self):
        self.sounds = {}
        self.ok = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            self.channels = pygame.mixer.get_init()[2]
            self.ok = True
        except pygame.error:
            return
        defs = {
            "shot": ([(3200, 900, 0.09)], 0.28, "noise"),
            "shotgun": ([(2600, 400, 0.2)], 0.4, "noise"),
            "rifle": ([(3600, 1200, 0.06), (900, 500, 0.05)], 0.3, "noise"),
            "enemy_shot": ([(2200, 600, 0.07)], 0.16, "noise"),
            "hit": ([(420, 200, 0.06)], 0.2, "square"),
            "kill": ([(600, 120, 0.2)], 0.22, "tri"),
            "boom": ([(900, 60, 0.6)], 0.5, "noise"),
            "bomb": ([(1200, 40, 1.0)], 0.55, "noise"),
            "pickup": ([(660, 880, 0.06), (880, 1320, 0.1)], 0.2, "square"),
            "hurt": ([(300, 90, 0.3)], 0.3, "square"),
            "die": ([(500, 60, 0.9)], 0.3, "tri"),
            "boss": ([(110, 90, 0.5), (90, 70, 0.6)], 0.35, "square"),
            "clear": ([(523, 523, 0.12), (659, 659, 0.12), (784, 784, 0.12), (1047, 1047, 0.3)], 0.22, "square"),
            "start": ([(294, 294, 0.12), (392, 392, 0.12), (440, 440, 0.12), (587, 587, 0.3)], 0.22, "square"),
            "life": ([(660, 660, 0.08), (880, 880, 0.08), (1320, 1320, 0.2)], 0.22, "square"),
            "tick": ([(1500, 1500, 0.03)], 0.1, "square"),
        }
        for name, (parts, vol, wave) in defs.items():
            mono = _make(parts, vol, wave)
            if self.channels == 2:
                stereo = array.array("h")
                for v in mono:
                    stereo.append(v)
                    stereo.append(v)
                mono = stereo
            self.sounds[name] = pygame.mixer.Sound(buffer=mono.tobytes())

    def play(self, name):
        if self.ok and name in self.sounds:
            self.sounds[name].play()
