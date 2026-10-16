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
        for i in range(n):
            t = i / n
            f = f0 + (f1 - f0) * t
            phase += f / RATE
            if f <= 0:
                v = 0.0
            elif wave == "noise":
                v = random.uniform(-1, 1)
            elif wave == "tri":
                v = 4 * abs((phase % 1) - 0.5) - 1
            else:
                v = 1.0 if (phase % 1) < 0.5 else -1.0
            buf.append(int(v * ((1 - t) ** 0.6) * vol * 32767))
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
            "jump": ([(260, 640, 0.13)], 0.2, "square"),
            "egg": ([(880, 1180, 0.06), (1180, 1760, 0.09)], 0.22, "square"),
            "grain": ([(620, 760, 0.05)], 0.18, "tri"),
            "die": ([(520, 70, 0.8)], 0.3, "tri"),
            "clear": ([(523, 523, 0.1), (659, 659, 0.1), (784, 784, 0.1), (1047, 1047, 0.25)], 0.22, "square"),
            "bird": ([(1100, 380, 0.28), (900, 300, 0.25)], 0.25, "square"),
            "life": ([(660, 660, 0.08), (880, 880, 0.08), (1320, 1320, 0.2)], 0.22, "square"),
            "start": ([(392, 392, 0.1), (523, 523, 0.1), (659, 659, 0.1), (784, 784, 0.3)], 0.22, "square"),
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
