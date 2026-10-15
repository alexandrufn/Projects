"""Synthesised sound effects and music (no audio files needed). Rendered once, cached on disk."""
import math
import os
import random
from array import array

import pygame

from config import SAVE_DIR

CACHE_VERSION = 1
TAU = math.tau
NAMES = ("punch", "kick", "whoosh", "hurt", "die", "knife", "jump", "land", "grip", "block", "gong", "roar", "fire",
         "boom", "win", "lose", "blip", "select", "tick", "shake", "break", "spark", "music_temple", "music_boss")


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


class Audio:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self.music_name = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2, 512)
            init = pygame.mixer.get_init()
            if init:
                self.rate, _, self.channels = init
                self.enabled = True
        except pygame.error:
            return
        pygame.mixer.set_num_channels(20)
        pygame.mixer.set_reserved(1)
        self.music_ch = pygame.mixer.Channel(0)
        self.rnd = random.Random(1983)
        self._load()

    # ------------------------------------------------------------------ utils
    def _sound(self, buf, peak=0.9):
        m = max(1e-6, max(abs(v) for v in buf))
        k = 32767 * peak / m
        mono = array("h", (int(v * k) for v in buf))
        if self.channels == 2:
            st = array("h", bytes(len(mono) * 4))
            st[0::2] = mono
            st[1::2] = mono
            mono = st
        return pygame.mixer.Sound(buffer=mono.tobytes())

    def _noise(self, dur, decay, lp, amp=1.0):
        n = int(dur * self.rate)
        out, y, r, rate = [0.0] * n, 0.0, self.rnd.uniform, self.rate
        for i in range(n):
            y += lp * (r(-1, 1) - y)
            out[i] = y * amp * math.exp(-decay * i / rate)
        return out

    def _tone(self, dur, freq, decay, amp=1.0, wave="sin", f_end=None):
        n = int(dur * self.rate)
        out, ph, rate = [0.0] * n, 0.0, self.rate
        for i in range(n):
            t = i / rate
            f = freq if f_end is None else freq + (f_end - freq) * (i / n)
            ph = (ph + f / rate) % 1.0
            if wave == "sin":
                v = math.sin(TAU * ph)
            elif wave == "sq":
                v = 1.0 if ph < 0.5 else -1.0
            elif wave == "tri":
                v = 4 * abs(ph - 0.5) - 1
            else:
                v = 2 * ph - 1
            out[i] = v * amp * math.exp(-decay * t)
        return out

    @staticmethod
    def _mix(*parts):
        out = [0.0] * max(len(p) for p in parts)
        for p in parts:
            for i, v in enumerate(p):
                out[i] += v
        return out

    @staticmethod
    def _place(buf, part, at, rate, wrap=False):
        start = int(at * rate)
        if wrap:
            n = len(buf)
            for i, v in enumerate(part):
                buf[(start + i) % n] += v
            return
        if start + len(part) > len(buf):
            buf.extend([0.0] * (start + len(part) - len(buf)))
        for i, v in enumerate(part):
            buf[start + i] += v

    # --------------------------------------------------------------- caching
    def _load(self):
        cache = os.path.join(SAVE_DIR, "sfx_v%d_%d_%d" % (CACHE_VERSION, self.rate, self.channels))
        try:
            for n in NAMES:
                with open(os.path.join(cache, n + ".raw"), "rb") as f:
                    self.sounds[n] = pygame.mixer.Sound(buffer=f.read())
        except (OSError, pygame.error):
            self.sounds.clear()
            self._synth()
            try:
                os.makedirs(cache, exist_ok=True)
                for n in NAMES:
                    with open(os.path.join(cache, n + ".raw"), "wb") as f:
                        f.write(self.sounds[n].get_raw())
            except OSError:
                pass

    # ----------------------------------------------------------------- sounds
    def _synth(self):
        S, R = self.sounds, self.rate
        S["punch"] = self._sound(self._mix(self._noise(0.07, 55, 0.7, 1.0), self._tone(0.12, 130, 28, 0.9)), 0.8)
        S["kick"] = self._sound(self._mix(self._noise(0.11, 38, 0.5, 1.2), self._tone(0.18, 85, 20, 1.2)), 0.9)
        n = int(0.2 * R)
        wh, y = [0.0] * n, 0.0
        for i in range(n):
            t = i / n
            y += (0.08 + 0.5 * t) * (self.rnd.uniform(-1, 1) - y)
            wh[i] = y * math.sin(math.pi * t) ** 1.5
        S["whoosh"] = self._sound(wh, 0.4)
        S["hurt"] = self._sound(self._mix(self._noise(0.25, 16, 0.25, 1.4), self._tone(0.3, 70, 12, 1.2),
                                          self._tone(0.18, 420, 22, 0.4, "sq", f_end=200)), 0.9)
        S["die"] = self._sound(self._mix(self._tone(0.4, 520, 6, 0.8, "saw", f_end=90), self._noise(0.3, 12, 0.3, 0.8)), 0.6)
        S["knife"] = self._sound(self._mix(self._tone(0.16, 2200, 12, 0.5, "sq", f_end=1100), self._noise(0.1, 30, 0.9, 0.3)), 0.3)
        S["jump"] = self._sound(self._tone(0.14, 260, 9, 1.0, "sq", f_end=700), 0.2)
        S["land"] = self._sound(self._noise(0.07, 60, 0.3, 1.0), 0.35)
        grip = self._tone(0.28, 95, 5, 1.0, "saw")
        S["grip"] = self._sound([v * (0.6 + 0.4 * math.sin(i / R * TAU * 22)) for i, v in enumerate(grip)], 0.4)
        S["block"] = self._sound(self._mix(self._tone(0.2, 1600, 26, 0.8, "sq"), self._tone(0.2, 2400, 30, 0.4),
                                           self._noise(0.05, 80, 0.9, 0.7)), 0.45)
        n = int(2.4 * R)
        bell = [0.0] * n
        for mul, amp, dec in ((0.5, 0.5, 1.0), (1.0, 1.0, 1.6), (1.19, 0.6, 2.3), (1.56, 0.4, 2.8), (2.0, 0.3, 3.4)):
            w = TAU * 146.0 * mul / R
            for i in range(n):
                bell[i] += math.sin(w * i) * amp * math.exp(-dec * i / R)
        S["gong"] = self._sound(self._mix(bell, self._noise(0.05, 60, 0.6, 0.6)), 0.8)
        S["roar"] = self._sound(self._mix(self._tone(0.7, 150, 3, 1.0, "saw", f_end=55), self._noise(0.7, 4, 0.2, 0.9)), 0.7)
        S["fire"] = self._sound(self._noise(0.8, 2.5, 0.22, 1.0), 0.45)
        S["boom"] = self._sound(self._mix(self._noise(0.5, 7, 0.12, 2.0), self._tone(0.5, 52, 6, 1.4)), 0.95)
        win = []
        for k, m in enumerate((72, 76, 79, 84, 79, 84, 88)):
            self._place(win, self._tone(0.5 if k == 6 else 0.13, midi(m), 3, 1.0, "sq"), k * 0.11, R)
        S["win"] = self._sound(win, 0.3)
        lose = []
        for k, m in enumerate((67, 64, 60, 55)):
            self._place(lose, self._tone(1.0 if k == 3 else 0.4, midi(m), 1.5, 1.0, "saw"), k * 0.4, R)
        S["lose"] = self._sound(lose, 0.3)
        S["blip"] = self._sound(self._tone(0.05, 900, 30, 1.0, "sq"), 0.18)
        sel = []
        self._place(sel, self._tone(0.07, 660, 20, 1.0, "sq"), 0, R)
        self._place(sel, self._tone(0.12, 990, 18, 1.0, "sq"), 0.06, R)
        S["select"] = self._sound(sel, 0.22)
        S["tick"] = self._sound(self._tone(0.05, 1600, 70, 1.0), 0.25)
        S["shake"] = self._sound(self._tone(0.05, 340, 50, 1.0, "tri"), 0.3)
        S["break"] = self._sound(self._mix(self._noise(0.22, 14, 0.5, 1.2), self._tone(0.1, 200, 30, 0.5)), 0.7)
        S["spark"] = self._sound(self._mix(self._tone(0.18, 1900, 18, 1.0, "sq", f_end=3000), self._noise(0.04, 80, 0.9, 0.4)), 0.25)
        S["music_temple"] = self._sound(self._song(104, False), 0.5)
        S["music_boss"] = self._sound(self._song(150, True), 0.55)

    def _pluck(self, f, dur, amp=1.0):
        n = int(dur * self.rate)
        out = [0.0] * n
        ph, rate = 0.0, self.rate
        for i in range(n):
            t = i / rate
            ph += TAU * f / rate
            out[i] = (math.sin(ph) + 0.5 * math.sin(2 * ph) * math.exp(-8 * t) + 0.25 * math.sin(3 * ph)
                      * math.exp(-14 * t)) * amp * math.exp(-5.5 * t) * min(1.0, t * 400)
        return out

    def _song(self, bpm, boss):
        """A looping pentatonic piece: plucked melody, drone bass and a drum pattern."""
        R = self.rate
        beat = 60.0 / bpm
        bars = 8
        total = int(bars * 4 * beat * R)
        out = [0.0] * total
        scale = (0, 3, 5, 7, 10)               # minor pentatonic
        root = 50 if not boss else 45          # D / A
        mel_a = [(0, 1), (2, 0.5), (3, 0.5), (4, 1), (3, 1), (2, 1), (1, 1), (0, 2), (1, 1), (2, 1),
                 (3, 2), (2, 1), (1, 1), (0, 1.5), (1, 0.5), (2, 1), (4, 1), (5, 1), (4, 1), (2, 1), (0, 3), ]
        rnd = random.Random(7 if not boss else 11)
        t = 0.0
        idx = 0
        while t < bars * 4 * beat - 0.01:
            if boss:
                step = 0.5
                deg = rnd.choice((0, 0, 2, 3, 4, 5, 6)) if idx % 4 else 0
                note = root + 24 + scale[deg % 5] + 12 * (deg // 5)
                self._place(out, self._pluck(midi(note), 0.28, 0.5), t * beat, R, True)
                t += step
            else:
                d, dur = mel_a[idx % len(mel_a)]
                note = root + 24 + scale[d % 5] + 12 * (d // 5)
                self._place(out, self._pluck(midi(note), dur * beat * 0.95, 0.55), t * beat, R, True)
                t += dur
            idx += 1
        # bass
        for bar in range(bars):
            r = root - 12 + (0, 0, 5, 3, 0, 0, 7, 5)[bar]
            for b in range(8 if boss else 4):
                at = (bar * 4 + b * (0.5 if boss else 1)) * beat
                note = r + (0 if b % 2 == 0 else (12 if boss else 7))
                self._place(out, self._tone(beat * (0.4 if boss else 0.9), midi(note), 5, 0.4, "tri"), at, R, True)
        # drums
        kick = self._mix(self._tone(0.16, 120, 24, 1.0, f_end=50), self._noise(0.02, 200, 0.5, 0.5))
        snare = self._mix(self._noise(0.12, 28, 0.6, 0.7), self._tone(0.08, 190, 40, 0.4))
        hat = self._noise(0.03, 150, 0.95, 0.25)
        for bar in range(bars):
            for b in range(8):
                at = (bar * 4 + b * 0.5) * beat
                if b in (0, 4) or (boss and b == 6):
                    self._place(out, kick, at, R, True)
                if b in (2, 6) and (boss or bar % 2):
                    self._place(out, snare, at, R, True)
                if boss or b % 2 == 1:
                    self._place(out, hat, at, R, True)
        # gentle pad drone
        drone = self._tone(4 * beat, midi(root - 12), 0, 0.12, "sin")
        for bar in range(0, bars, 1):
            self._place(out, drone, bar * 4 * beat, R, True)
        return out

    # --------------------------------------------------------------- playback
    def play(self, name, vol=1.0):
        if not self.enabled:
            return
        s = self.sounds.get(name)
        if s:
            ch = s.play()
            if ch:
                ch.set_volume(vol)

    def music(self, name):
        if not self.enabled or name == self.music_name:
            return
        self.music_name = name
        if name is None:
            self.music_ch.fadeout(500)
            return
        self.music_ch.play(self.sounds["music_" + name], loops=-1, fade_ms=500)
        self.music_ch.set_volume(0.5)
