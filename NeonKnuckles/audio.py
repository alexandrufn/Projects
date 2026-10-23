"""Synthesised sound effects and 16-bit style music (no audio files needed). Rendered once, cached on disk."""
import math
import os
import random
from array import array

import pygame

from config import SAVE_DIR

CACHE_VERSION = 1
TAU = math.tau
NAMES = ("punch", "hit", "kick", "whoosh", "slash", "bat", "whip", "hurt", "thud", "jump", "land", "grab", "throw",
         "knife", "break", "splash", "steam", "pickup", "eat", "block", "roar", "boom", "go", "select", "blip",
         "win", "lose", "coin", "shake",
         "music_title", "music_street", "music_factory", "music_final", "music_boss")
MINOR = (0, 2, 3, 5, 7, 8, 10)
REST = None


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def degree(d):
    return MINOR[d % 7] + 12 * (d // 7)


# Melodies: (scale degree or REST, beats). Each line is one 4/4 bar.
MEL_STREET = [
    (0, 1), (0, .5), (2, .5), (3, 1), (4, 1),
    (3, .5), (2, .5), (0, 1), (-1, 1), (0, 1),
    (4, 1), (4, .5), (5, .5), (6, 1), (7, 1),
    (6, .5), (5, .5), (4, 1), (2, 1.5), (REST, .5),
    (0, 1), (0, .5), (2, .5), (3, 1), (4, 1),
    (3, .5), (2, .5), (0, 1), (-1, 1), (-3, 1),
    (-2, 1), (0, .5), (2, .5), (4, 1), (3, 1),
    (2, .5), (1, .5), (0, 3),
]
MEL_FACTORY = [
    (0, .5), (REST, .5), (0, .5), (3, .5), (2, 1), (0, 1),
    (4, .5), (REST, .5), (4, .5), (3, .5), (2, 2),
    (0, .5), (REST, .5), (0, .5), (3, .5), (5, 1), (4, 1),
    (3, .5), (2, .5), (3, .5), (2, .5), (0, 2),
    (7, 1), (6, .5), (4, .5), (5, 1), (4, 1),
    (3, 1), (2, .5), (0, .5), (2, 2),
    (4, .5), (5, .5), (6, .5), (7, .5), (8, 1), (7, 1),
    (6, .5), (5, .5), (4, 1), (4, 2),
]
MEL_FINAL = [
    (4, 1.5), (3, .5), (2, 1), (0, 1),
    (1, 1.5), (2, .5), (-1, 2),
    (4, 1.5), (5, .5), (6, 1), (7, 1),
    (8, 1), (7, 1), (6, 2),
    (7, 1.5), (6, .5), (4, 1), (2, 1),
    (3, 1.5), (2, .5), (0, 2),
    (-1, 1), (0, 1), (2, 1), (4, 1),
    (3, 2), (2, 1), (0, 1),
]
MEL_TITLE = [
    (0, 2), (2, 1), (3, 1), (4, 3), (3, 1),
    (2, 2), (0, 2), (-1, 4),
    (0, 2), (2, 1), (3, 1), (4, 2), (7, 2),
    (6, 2), (4, 2), (4, 4),
]
BASS_STREET = (0, 0, -4, -4, -2, -2, -5, -5)
BASS_FACTORY = (0, 0, 0, 0, 3, 3, -2, -2)
BASS_FINAL = (0, -4, -2, -5, 0, -4, -7, -5)


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
        self.rnd = random.Random(1987)
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

    def _tone(self, dur, freq, decay, amp=1.0, wave="sin", f_end=None, duty=0.5, vib=0.0):
        n = int(dur * self.rate)
        out, ph, rate = [0.0] * n, 0.0, self.rate
        for i in range(n):
            t = i / rate
            f = freq if f_end is None else freq + (f_end - freq) * (i / n)
            if vib:
                f *= 1 + vib * math.sin(TAU * 5.5 * t) * min(1.0, t * 4)
            ph = (ph + f / rate) % 1.0
            if wave == "sin":
                v = math.sin(TAU * ph)
            elif wave == "sq":
                v = 1.0 if ph < duty else -1.0
            elif wave == "tri":
                v = 4 * abs(ph - 0.5) - 1
            else:
                v = 2 * ph - 1
            out[i] = v * amp * math.exp(-decay * t) * min(1.0, t * 600)
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
        S["punch"] = self._sound(self._mix(self._noise(0.06, 60, 0.7, 1.0), self._tone(0.10, 150, 30, 0.9)), 0.75)
        S["hit"] = self._sound(self._mix(self._noise(0.12, 34, 0.55, 1.3), self._tone(0.2, 90, 18, 1.3),
                                         self._tone(0.06, 900, 60, 0.3, "sq")), 0.95)
        S["kick"] = self._sound(self._mix(self._noise(0.10, 40, 0.5, 1.2), self._tone(0.16, 100, 22, 1.1)), 0.85)
        n = int(0.18 * R)
        wh, y = [0.0] * n, 0.0
        for i in range(n):
            t = i / n
            y += (0.08 + 0.5 * t) * (self.rnd.uniform(-1, 1) - y)
            wh[i] = y * math.sin(math.pi * t) ** 1.5
        S["whoosh"] = self._sound(wh, 0.4)
        S["slash"] = self._sound(self._mix(self._noise(0.14, 30, 0.95, 0.9), self._tone(0.12, 2600, 25, 0.4, "saw",
                                                                                       f_end=900)), 0.6)
        S["bat"] = self._sound(self._mix(self._tone(0.18, 210, 22, 1.0, "tri"), self._noise(0.08, 50, 0.6, 1.0),
                                         self._tone(0.1, 520, 30, 0.4)), 0.85)
        S["whip"] = self._sound(self._mix(self._noise(0.08, 50, 0.98, 1.0), self._tone(0.12, 3000, 30, 0.5, "sq",
                                                                                      f_end=1400)), 0.55)
        S["hurt"] = self._sound(self._mix(self._noise(0.22, 16, 0.25, 1.3), self._tone(0.26, 260, 9, 0.8, "sq",
                                                                                      f_end=120, duty=0.3)), 0.8)
        S["thud"] = self._sound(self._mix(self._noise(0.16, 26, 0.18, 1.4), self._tone(0.2, 60, 16, 1.4)), 0.9)
        S["jump"] = self._sound(self._tone(0.12, 300, 10, 1.0, "sq", f_end=640, duty=0.25), 0.2)
        S["land"] = self._sound(self._noise(0.06, 60, 0.3, 1.0), 0.35)
        grip = self._tone(0.22, 110, 6, 1.0, "saw")
        S["grab"] = self._sound([v * (0.6 + 0.4 * math.sin(i / R * TAU * 24)) for i, v in enumerate(grip)], 0.4)
        S["throw"] = self._sound(self._mix(self._tone(0.3, 180, 6, 0.8, "saw", f_end=60), wh + [0.0] * 3000), 0.6)
        S["knife"] = self._sound(self._mix(self._tone(0.14, 2400, 14, 0.5, "sq", f_end=1300),
                                           self._noise(0.1, 30, 0.9, 0.3)), 0.3)
        S["break"] = self._sound(self._mix(self._noise(0.3, 12, 0.55, 1.3), self._tone(0.08, 300, 40, 0.6),
                                           self._tone(0.12, 170, 30, 0.6)), 0.8)
        sp = self._noise(0.6, 4, 0.35, 1.0)
        S["splash"] = self._sound([v * min(1.0, i / (0.02 * R)) for i, v in enumerate(sp)], 0.6)
        st = self._noise(0.9, 2.5, 0.9, 1.0)
        S["steam"] = self._sound([v * min(1.0, i / (0.06 * R)) for i, v in enumerate(st)], 0.35)
        pk = []
        for k, m in enumerate((76, 83)):
            self._place(pk, self._tone(0.08, midi(m), 18, 1.0, "sq", duty=0.25), k * 0.05, R)
        S["pickup"] = self._sound(pk, 0.22)
        eat = []
        for k, m in enumerate((72, 76, 79, 84)):
            self._place(eat, self._tone(0.08, midi(m), 14, 1.0, "sq"), k * 0.06, R)
        S["eat"] = self._sound(eat, 0.25)
        S["block"] = self._sound(self._mix(self._tone(0.2, 1700, 26, 0.8, "sq"), self._tone(0.2, 2550, 30, 0.4),
                                           self._noise(0.05, 80, 0.9, 0.7)), 0.45)
        S["roar"] = self._sound(self._mix(self._tone(0.7, 140, 3, 1.0, "saw", f_end=60), self._noise(0.7, 4, 0.2, 0.9)), 0.7)
        S["boom"] = self._sound(self._mix(self._noise(0.5, 7, 0.12, 2.0), self._tone(0.5, 50, 6, 1.4)), 0.95)
        go = []
        for k in range(2):
            self._place(go, self._tone(0.12, midi(84), 10, 1.0, "sq"), k * 0.2, R)
        S["go"] = self._sound(go, 0.25)
        S["select"] = self._sound(self._mix(self._tone(0.08, 660, 20, 1.0, "sq"),
                                            [0.0] * int(0.05 * R) + self._tone(0.12, 990, 18, 1.0, "sq")), 0.22)
        S["blip"] = self._sound(self._tone(0.04, 900, 30, 1.0, "sq"), 0.16)
        win = []
        for k, m in enumerate((67, 71, 74, 79, 74, 79, 83)):
            self._place(win, self._tone(0.6 if k == 6 else 0.12, midi(m), 3, 1.0, "sq", duty=0.25, vib=0.01), k * 0.1, R)
        S["win"] = self._sound(win, 0.3)
        lose = []
        for k, m in enumerate((64, 63, 62, 61)):
            self._place(lose, self._tone(1.0 if k == 3 else 0.32, midi(m), 1.5, 1.0, "sq", vib=0.02), k * 0.34, R)
        S["lose"] = self._sound(lose, 0.3)
        coin = []
        self._place(coin, self._tone(0.06, midi(88), 20, 1.0, "sq"), 0, R)
        self._place(coin, self._tone(0.3, midi(95), 9, 1.0, "sq"), 0.06, R)
        S["coin"] = self._sound(coin, 0.22)
        S["shake"] = self._sound(self._tone(0.05, 340, 50, 1.0, "tri"), 0.3)
        S["music_title"] = self._sound(self._song(84, 45, MEL_TITLE, BASS_STREET[::2], "title"), 0.5)
        S["music_street"] = self._sound(self._song(132, 45, MEL_STREET, BASS_STREET, "street"), 0.5)
        S["music_factory"] = self._sound(self._song(120, 40, MEL_FACTORY, BASS_FACTORY, "factory"), 0.5)
        S["music_final"] = self._sound(self._song(138, 47, MEL_FINAL, BASS_FINAL, "street"), 0.5)
        S["music_boss"] = self._sound(self._song(152, 42, None, (0, 0, 1, 1, 0, 0, -2, -1), "boss"), 0.55)

    def _song(self, bpm, root, melody, bass, style):
        """A looping 8-bar tune: pulse lead with vibrato, saw bass, noise drums - Mega Drive flavoured."""
        R = self.rate
        beat = 60.0 / bpm
        bars = 8
        total = int(bars * 4 * beat * R)
        out = [0.0] * total
        # lead
        if melody is not None:
            t = 0.0
            for d, dur in melody:
                if d is not None:
                    f = midi(root + 24 + degree(d))
                    note = self._tone(dur * beat * 0.92, f, 1.2 if style != "title" else 0.6, 0.5, "sq",
                                      duty=0.25 if style != "title" else 0.5, vib=0.006)
                    echo = [v * 0.3 for v in note]
                    self._place(out, note, t * beat, R, True)
                    self._place(out, echo, (t + 0.75) * beat, R, True)
                t += dur
        else:
            arp = (0, 3, 7, 12, 7, 3, 0, 3)
            for bar in range(bars):
                r = root + 24 + bass[bar]
                for k in range(8):
                    n = r + arp[(k + bar) % 8] + (12 if bar >= 4 and k % 4 == 3 else 0)
                    self._place(out, self._tone(beat * 0.45, midi(n), 5, 0.42, "sq", duty=0.25), (bar * 4 + k * 0.5) * beat,
                                R, True)
        # bass
        for bar in range(bars):
            r = root - 12 + bass[bar % len(bass)]
            steps = 8 if style in ("street", "boss", "factory") else 2
            for b in range(steps):
                at = (bar * 4 + b * (4 / steps)) * beat
                n = r + (12 if (style == "street" and b % 2) or (style == "boss" and b % 4 == 2) else 0)
                ln = beat * (0.45 if steps == 8 else 1.9)
                self._place(out, self._tone(ln, midi(n), 6 if steps == 8 else 1.2, 0.55, "saw"), at, R, True)
        # pad for the title
        if style == "title":
            for bar in range(bars):
                r = root + 12 + bass[bar % len(bass)]
                for iv in (0, 3, 7):
                    self._place(out, self._tone(4 * beat, midi(r + iv), 0.5, 0.12, "tri"), bar * 4 * beat, R, True)
        # drums
        kick = self._mix(self._tone(0.14, 130, 26, 1.0, f_end=45), self._noise(0.02, 200, 0.5, 0.5))
        snare = self._mix(self._noise(0.14, 24, 0.7, 0.8), self._tone(0.08, 200, 40, 0.4))
        hat = self._noise(0.025, 170, 0.97, 0.22)
        clank = self._mix(self._tone(0.1, 820, 30, 0.3, "sq"), self._tone(0.1, 1230, 34, 0.2, "sq"))
        for bar in range(bars):
            for b in range(16):
                at = (bar * 4 + b * 0.25) * beat
                if style == "title":
                    if b == 0:
                        self._place(out, kick, at, R, True)
                    if b == 8 and bar % 2:
                        self._place(out, snare, at, R, True)
                    continue
                if b in (0, 8) or (b == 10 and style != "factory") or (style == "boss" and b in (4, 12)):
                    self._place(out, kick, at, R, True)
                if b in (4, 12) or (style == "boss" and b == 14):
                    self._place(out, snare, at, R, True)
                if b % 2 == 0 or style == "boss":
                    self._place(out, hat, at, R, True)
                if style == "factory" and b in (6, 14):
                    self._place(out, clank, at, R, True)
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
        self.music_ch.play(self.sounds["music_" + name], loops=-1, fade_ms=400)
        self.music_ch.set_volume(0.45)
