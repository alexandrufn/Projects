"""Synthesised sound effects and music: no audio files required."""
import math
import os
import random
from array import array

import pygame

from config import SAVE_DIR

CACHE_VERSION = 2

TAU = math.tau


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


class Audio:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self.music = None
        self.wind = None
        self.music_ch = None
        self.wind_ch = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2, 512)
            init = pygame.mixer.get_init()
            if init:
                self.rate, _, self.channels = init
                self.enabled = True
        except pygame.error:
            self.enabled = False
        if self.enabled:
            pygame.mixer.set_num_channels(20)
            pygame.mixer.set_reserved(2)
            self.music_ch = pygame.mixer.Channel(0)
            self.wind_ch = pygame.mixer.Channel(1)
            self.rnd = random.Random(1983)
            self._build()

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
        out = [0.0] * n
        y = 0.0
        r = self.rnd.uniform
        rate = self.rate
        for i in range(n):
            y += lp * (r(-1, 1) - y)
            out[i] = y * amp * math.exp(-decay * i / rate)
        return out

    def _tone(self, dur, freq, decay, amp=1.0, wave="sin"):
        n = int(dur * self.rate)
        rate = self.rate
        out = [0.0] * n
        for i in range(n):
            t = i / rate
            ph = (freq * t) % 1.0
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
        n = max(len(p) for p in parts)
        out = [0.0] * n
        for p in parts:
            for i, v in enumerate(p):
                out[i] += v
        return out

    def _place(self, buf, part, at):
        start = int(at * self.rate)
        need = start + len(part)
        if need > len(buf):
            buf.extend([0.0] * (need - len(buf)))
        for i, v in enumerate(part):
            buf[start + i] += v

    # ----------------------------------------------------------------- sounds
    def _build(self):
        cache = os.path.join(SAVE_DIR, "sfx_v%d_%d_%d" % (CACHE_VERSION, self.rate, self.channels))
        names = ("shot", "ricochet", "hit", "chip", "wood", "tick", "click", "reload", "jam", "bell",
                 "blip", "select", "win", "lose", "grunt", "neigh", "music", "wind")
        try:
            for n in names:
                with open(os.path.join(cache, n + ".raw"), "rb") as f:
                    self.sounds[n] = pygame.mixer.Sound(buffer=f.read())
        except (OSError, pygame.error):
            self.sounds.clear()
            self._synth()
            try:
                os.makedirs(cache, exist_ok=True)
                for n in names:
                    with open(os.path.join(cache, n + ".raw"), "wb") as f:
                        f.write(self.sounds[n].get_raw())
            except OSError:
                pass
        self.music = self.sounds.pop("music")
        self.wind = self.sounds.pop("wind")

    def _synth(self):
        S = self.sounds
        rate = self.rate
        S["shot"] = self._sound(self._mix(
            self._noise(0.05, 60, 0.95, 1.0),
            self._noise(0.45, 9, 0.12, 4.0),
            self._tone(0.3, 70, 16, 0.7)), 0.95)

        n = int(0.55 * rate)
        ph = 0.0
        ric = [0.0] * n
        for i in range(n):
            t = i / rate
            ph += TAU * (2600 * math.exp(-3 * t) + 700) / rate
            ric[i] = math.sin(ph) * math.exp(-5 * t) * min(1.0, t * 80)
        S["ricochet"] = self._sound(self._mix(ric, self._noise(0.05, 50, 0.8, 0.3)), 0.5)

        S["hit"] = self._sound(self._mix(self._tone(0.3, 55, 14, 1.0), self._noise(0.25, 20, 0.2, 2.0)), 0.85)
        S["chip"] = self._sound(self._noise(0.09, 45, 0.7), 0.45)
        S["wood"] = self._sound(self._mix(self._noise(0.15, 28, 0.35, 1.5), self._tone(0.12, 180, 40, 0.6)), 0.6)
        S["tick"] = self._sound(self._mix(self._tone(0.06, 1800, 80, 1.0), self._noise(0.02, 120, 0.9, 0.5)), 0.35)
        S["click"] = self._sound(self._noise(0.03, 150, 0.9), 0.45)

        reload_ = []
        self._place(reload_, self._noise(0.03, 150, 0.9), 0.0)
        for k in range(6):
            self._place(reload_, self._noise(0.02, 200, 0.9, 0.35), 0.06 + k * 0.035)
        self._place(reload_, self._noise(0.04, 120, 0.8, 1.0), 0.32)
        S["reload"] = self._sound(reload_, 0.5)

        jam = []
        self._place(jam, self._noise(0.03, 150, 0.9), 0.0)
        self._place(jam, self._tone(0.08, 300, 50, 0.6, "sq"), 0.1)
        S["jam"] = self._sound(jam, 0.45)

        # church bell for "DRAW!"
        n = int(2.6 * rate)
        bell = [0.0] * n
        f0 = 392.0
        partials = ((0.5, 0.5, 1.2), (1.0, 1.0, 1.8), (1.19, 0.6, 2.5), (1.56, 0.4, 3.0),
                    (2.0, 0.3, 3.5), (2.74, 0.2, 4.5))
        for mul, amp, dec in partials:
            w = TAU * f0 * mul / rate
            for i in range(n):
                bell[i] += math.sin(w * i) * amp * math.exp(-dec * i / rate)
        S["bell"] = self._sound(self._mix(bell, self._noise(0.03, 80, 0.9, 0.6)), 0.7)

        S["blip"] = self._sound(self._tone(0.05, 880, 30, 1.0, "sq"), 0.18)
        sel = []
        self._place(sel, self._tone(0.07, 660, 20, 1.0, "sq"), 0)
        self._place(sel, self._tone(0.12, 990, 18, 1.0, "sq"), 0.06)
        S["select"] = self._sound(sel, 0.22)

        win = []
        for k, m in enumerate((72, 76, 79, 84)):
            d = 0.6 if k == 3 else 0.14
            self._place(win, self._tone(d, midi(m), 3, 1.0, "sq"), k * 0.13)
        S["win"] = self._sound(win, 0.3)

        lose = []
        for k, m in enumerate((67, 66, 65, 64)):
            d = 1.0 if k == 3 else 0.36
            part = self._tone(d, midi(m), 1.5, 1.0, "saw")
            self._place(lose, part, k * 0.38)
        S["lose"] = self._sound(lose, 0.3)

        # boss pain: a gravelly, falling grunt
        n = int(0.32 * rate)
        ph, grunt, y = 0.0, [0.0] * n, 0.0
        for i in range(n):
            t = i / rate
            ph = (ph + (150 - 180 * t) / rate) % 1.0
            y += 0.25 * (self.rnd.uniform(-1, 1) - y)
            env = min(1.0, t / 0.02) * math.exp(-5 * t)
            grunt[i] = ((2 * ph - 1) * 0.8 + y * 0.6) * env
        S["grunt"] = self._sound(grunt, 0.6)

        # horse whinny: wobbling pitch that rises then falls
        n = int(0.8 * rate)
        ph, neigh = 0.0, [0.0] * n
        for i in range(n):
            t = i / rate
            f = (650 + 350 * math.sin(math.pi * min(1.0, t / 0.8))) * (1 + 0.08 * math.sin(TAU * 13 * t))
            ph += TAU * f / rate
            env = min(1.0, t / 0.05) * min(1.0, (0.8 - t) / 0.25)
            neigh[i] = (math.sin(ph) + 0.4 * math.sin(2 * ph) + 0.2 * math.sin(3 * ph)) * env
        S["neigh"] = self._sound(neigh, 0.4)

        S["music"] = self._sound(self._compose(), 0.55)
        S["wind"] = self._sound(self._wind(), 0.35)

    def _compose(self):
        """A short spaghetti-western loop: whistled melody over boom-chick guitar."""
        rate = self.rate
        beat = 60 / 96
        melody = [(69, 1), (72, .5), (74, .5), (76, 2), (79, 1), (76, 1), (74, 1), (72, 1),
                  (74, 1.5), (76, .5), (74, 1), (69, 1), (76, 4),
                  (69, 1), (72, .5), (74, .5), (76, 2), (79, 1), (81, 1), (79, 1), (76, 1),
                  (74, 1), (72, 1), (71, 1), (67, 1), (69, 4)]
        bass = [45, 48, 50, 40, 45, 48, 43, 45]
        total = int(32 * beat * rate)
        out = [0.0] * total

        t0 = 0.0
        for note, beats in melody:
            f = midi(note)
            dur = beats * beat
            n = int(dur * rate)
            start = int(t0 * rate)
            ph = 0.0
            for i in range(n):
                if start + i >= total:
                    break
                t = i / rate
                vib = 1 + (0.007 * math.sin(TAU * 5.5 * t) if t > 0.15 else 0)
                ph += TAU * f * vib / rate
                env = min(1.0, t / 0.04) * min(1.0, (dur - t) / 0.08)
                out[start + i] += (math.sin(ph) + 0.12 * math.sin(2 * ph)) * 0.3 * env
            t0 += dur

        for bar, root in enumerate(bass):
            for b, (note, amp) in enumerate(((root, 0.32), (None, 0), (root + 7, 0.25), (None, 0))):
                at = (bar * 4 + b) * beat
                if note is None:
                    part = self._noise(0.06, 60, 0.6, 0.08)
                else:
                    part = self._tone(beat * 1.6, midi(note), 3.5, amp, "tri")
                start = int(at * rate)
                for i, v in enumerate(part):
                    j = start + i
                    if j >= total:
                        j -= total  # wrap the tail so the loop is seamless
                    out[j] += v
        return out

    def _wind(self):
        rate = self.rate
        dur = 8.0
        n = int(dur * rate)
        fade = int(0.5 * rate)
        raw = [0.0] * (n + fade)
        y = 0.0
        r = self.rnd.uniform
        for i in range(n + fade):
            t = i / rate
            lp = 0.012 + 0.01 * (1 + math.sin(TAU * t / dur * 2))
            y += lp * (r(-1, 1) - y)
            raw[i] = y * (0.6 + 0.4 * math.sin(TAU * t / dur * 3 + 1))
        for i in range(fade):
            k = i / fade
            raw[i] = raw[i] * k + raw[n + i] * (1 - k)
        return raw[:n]

    # -------------------------------------------------------------- playback
    def play(self, name, vol=1.0):
        if not self.enabled:
            return
        s = self.sounds.get(name)
        if s:
            ch = s.play()
            if ch:
                ch.set_volume(vol)

    def play_music(self):
        if self.enabled and not self.music_ch.get_busy():
            self.wind_ch.stop()
            self.music_ch.play(self.music, loops=-1, fade_ms=600)
            self.music_ch.set_volume(0.55)

    def stop_music(self):
        if self.enabled:
            self.music_ch.fadeout(400)

    def start_wind(self):
        if self.enabled and not self.wind_ch.get_busy():
            self.wind_ch.play(self.wind, loops=-1, fade_ms=800)
            self.wind_ch.set_volume(0.35)

    def stop_wind(self):
        if self.enabled:
            self.wind_ch.fadeout(300)
