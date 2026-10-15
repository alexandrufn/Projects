"""Keyboard and gamepad mappings."""
import pygame
from pygame.locals import (K_w, K_a, K_s, K_d, K_r, K_f, K_v, K_UP, K_DOWN, K_LEFT, K_RIGHT, K_i, K_k,
                           K_COMMA, K_SPACE, K_RETURN, K_KP_ENTER, K_ESCAPE, K_BACKSPACE, K_p,
                           KEYDOWN, JOYHATMOTION, JOYBUTTONDOWN, KMOD_ALT)

P1_MOVE = dict(up=(K_w,), down=(K_s,), left=(K_a,), right=(K_d,))
P2_MOVE = dict(up=(K_UP,), down=(K_DOWN,), left=(K_LEFT,), right=(K_RIGHT,))
P1_FIRE = {K_r: "up", K_f: "straight", K_v: "down"}
P2_FIRE = {K_i: "up", K_k: "straight", K_COMMA: "down"}
SOLO_FIRE = {**P1_FIRE, **P2_FIRE, K_SPACE: "straight"}

# Xbox-style layout: A = straight, Y = up, B = down, X = straight
JOY_FIRE = {0: "straight", 2: "straight", 3: "up", 1: "down"}
JOY_START = 7
DEADZONE = 0.35


def _held(keys, codes):
    return any(keys[c] for c in codes)


def move_vector(keys, maps, joys=()):
    mx = my = 0.0
    for m in maps:
        mx += _held(keys, m["right"]) - _held(keys, m["left"])
        my += _held(keys, m["down"]) - _held(keys, m["up"])
    for j in joys:
        try:
            ax, ay = j.get_axis(0), j.get_axis(1)
            if abs(ax) > DEADZONE:
                mx += ax
            if abs(ay) > DEADZONE:
                my += ay
            if j.get_numhats():
                hx, hy = j.get_hat(0)
                mx += hx
                my -= hy
        except pygame.error:
            pass
    return max(-1.0, min(1.0, mx)), max(-1.0, min(1.0, my))


def menu_action(e):
    if e.type == KEYDOWN:
        if e.mod & KMOD_ALT:
            return None
        if e.key in (K_UP, K_w):
            return "up"
        if e.key in (K_DOWN, K_s):
            return "down"
        if e.key in (K_LEFT, K_a):
            return "left"
        if e.key in (K_RIGHT, K_d):
            return "right"
        if e.key in (K_RETURN, K_KP_ENTER, K_SPACE, K_f, K_k):
            return "ok"
        if e.key in (K_ESCAPE, K_BACKSPACE):
            return "back"
    elif e.type == JOYHATMOTION:
        hx, hy = e.value
        if hy == 1:
            return "up"
        if hy == -1:
            return "down"
        if hx == -1:
            return "left"
        if hx == 1:
            return "right"
    elif e.type == JOYBUTTONDOWN:
        if e.button in (0, JOY_START):
            return "ok"
        if e.button == 1:
            return "back"
    return None


def is_pause(e):
    return (e.type == KEYDOWN and e.key in (K_ESCAPE, K_p)) or (e.type == JOYBUTTONDOWN and e.button == JOY_START)
