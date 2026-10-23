"""Keyboard and gamepad input for two players.

With one player in the game, player 1 answers to both keyboard layouts. Player 2's START key
(Right Shift / keypad Enter, or Start on the second pad) always belongs to player 2 so they can join.
"""
import pygame

BUTTONS = ("left", "right", "up", "down", "punch", "kick", "jump", "start")

KEYMAPS = [
    dict(left=(pygame.K_a,), right=(pygame.K_d,), up=(pygame.K_w,), down=(pygame.K_s,),
         punch=(pygame.K_j, pygame.K_f), kick=(pygame.K_k, pygame.K_g), jump=(pygame.K_l, pygame.K_SPACE, pygame.K_h),
         start=(pygame.K_RETURN,)),
    dict(left=(pygame.K_LEFT,), right=(pygame.K_RIGHT,), up=(pygame.K_UP,), down=(pygame.K_DOWN,),
         punch=(pygame.K_KP1, pygame.K_COMMA, pygame.K_z), kick=(pygame.K_KP2, pygame.K_PERIOD, pygame.K_x),
         jump=(pygame.K_KP3, pygame.K_SLASH, pygame.K_c), start=(pygame.K_KP_ENTER, pygame.K_RSHIFT)),
]
# Xbox-style layout through SDL's joystick API: A=0 B=1 X=2 Y=3 Start=7
PAD_BUTTONS = {0: "jump", 1: "kick", 2: "punch", 3: "kick", 7: "start", 9: "start"}


class Pad:
    def __init__(self, idx):
        self.idx = idx
        self.down = set()
        self.prev = set()
        self.hit = set()

    def held(self, b):
        return b in self.down

    def pressed(self, b):
        return b in self.hit

    def any_attack(self):
        return bool(self.hit & {"punch", "kick", "jump", "start"})

    def axis(self):
        dx = (1 if "right" in self.down else 0) - (1 if "left" in self.down else 0)
        dz = (1 if "down" in self.down else 0) - (1 if "up" in self.down else 0)
        return dx, dz


class Controls:
    def __init__(self):
        self.pads = [Pad(0), Pad(1)]
        self.shared = True          # True while only player 1 is playing

    def _owner(self, map_idx, button):
        if self.shared and not (map_idx == 1 and button == "start"):
            return 0
        return map_idx

    def update(self, events, joysticks):
        events_hit = [set(), set()]
        for e in events:
            if e.type == pygame.KEYDOWN:
                for mi, km in enumerate(KEYMAPS):
                    for b, keys in km.items():
                        if e.key in keys:
                            events_hit[self._owner(mi, b)].add(b)
            elif e.type == pygame.JOYBUTTONDOWN:
                b = PAD_BUTTONS.get(e.button)
                idx = next((i for i, j in enumerate(joysticks) if j.get_instance_id() == e.instance_id), 0)
                if b and idx < 2:
                    events_hit[self._owner(idx, b)].add(b)
        keys = pygame.key.get_pressed()
        now = [set(), set()]
        for mi, km in enumerate(KEYMAPS):
            for b, ks in km.items():
                if any(keys[k] for k in ks):
                    now[self._owner(mi, b)].add(b)
        for ji, j in enumerate(joysticks[:2]):
            tgt = now[self._owner(ji, "left")]
            try:
                ax, ay = j.get_axis(0), j.get_axis(1)
                hx, hy = j.get_hat(0) if j.get_numhats() else (0, 0)
            except pygame.error:
                continue
            if ax < -0.45 or hx < 0:
                tgt.add("left")
            if ax > 0.45 or hx > 0:
                tgt.add("right")
            if ay < -0.45 or hy > 0:
                tgt.add("up")
            if ay > 0.45 or hy < 0:
                tgt.add("down")
            for bi, b in PAD_BUTTONS.items():
                if bi < j.get_numbuttons() and j.get_button(bi):
                    now[self._owner(ji, b)].add(b)
        for i, p in enumerate(self.pads):
            p.prev = p.down
            p.down = now[i]
            p.hit = (now[i] - p.prev) | events_hit[i]

    # --- menu helpers -----------------------------------------------------
    def menu_pressed(self, b):
        return any(p.pressed(b) for p in self.pads)

    def confirm(self):
        return any(p.pressed("start") or p.pressed("punch") or p.pressed("jump") for p in self.pads)
