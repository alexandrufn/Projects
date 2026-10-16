"""Game-wide constants and visual themes for Egg Rush Harry."""
import os

TITLE = "Egg Rush Harry"

# Logical (pixel-art) resolution. The window is scaled up with pygame.SCALED.
W, H = 320, 256
FPS = 60

TILE = 16
COLS = 20
OY = 16                          # top of the play field (a HUD bar sits above)
FLOOR_ROWS = (2, 5, 8, 11, 14)   # grid rows of the five floors, top to bottom
GROUND_ROW = FLOOR_ROWS[-1]

NUM_LAYOUTS = 8
NUM_LEVELS = 17                  # two rounds of the 8 layouts, then the boss
BOSS_LEVEL = 17
BIRD_FREE_FROM = 9               # the big bird escapes its cage from level 9 on

# Cage in the top-left corner (3 x 2 tiles, sitting on the top floor).
CAGE_RECT = (0, OY, 3 * TILE, 2 * TILE)
CAGE_CENTER = (24, OY + 18)

LIVES = 5
PLAYER_SPEED = 62.0
CLIMB_SPEED = 48.0
GRAVITY = 300.0
JUMP_V = 85.0          # apex ~12px: long enough to cross a 2-tile gap, too low to clear a hen

SCORE_EGG = 100
SCORE_GRAIN = 50
SCORE_TIME = 10
SCORE_CLEAR = 500
EXTRA_LIFE_EVERY = 10000

SAVE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "EggRushHarry")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")


def level_time(n):
    """Seconds allowed on level n (1-based)."""
    if n == BOSS_LEVEL:
        return 100
    return max(60, int(110 - 2.5 * (n - 1)))


def hen_count(n):
    if n == BOSS_LEVEL:
        return 5
    return min(7, 2 + (n - 1) // 3)


def hen_speed(n):
    return 24.0 + 1.8 * (n - 1)


def bird_speed(n):
    return min(50.0, 28.0 + 2.5 * (n - BIRD_FREE_FROM))


# Big Momma, the boss hen (level 17): five times the size of a normal hen.
MOMMA_SCALE = 5
MOMMA_SPEED = (32.0, 56.0)       # walking speed at the start / when only one egg is left
MOMMA_CHICK_EVERY = 9.0          # seconds between the chicks she clucks out
MOMMA_MAX_HENS = 9


# Visual themes, one per layout: sky gradient, silhouettes and platform wood.
THEMES = [
    dict(sky=((16, 20, 60), (96, 70, 130)), hill=((44, 40, 90), (30, 28, 66)), orb=(250, 244, 205), orb_pos=(262, 52),
         stars=True, plank=(150, 98, 58), grass=(84, 168, 74)),
    dict(sky=((60, 36, 90), (240, 130, 90)), hill=((120, 66, 98), (82, 44, 78)), orb=(255, 214, 140), orb_pos=(70, 150),
         stars=False, plank=(168, 108, 62), grass=(120, 170, 70)),
    dict(sky=((10, 30, 56), (40, 110, 130)), hill=((24, 70, 90), (16, 48, 68)), orb=(220, 240, 255), orb_pos=(246, 44),
         stars=True, plank=(120, 110, 100), grass=(70, 150, 100)),
    dict(sky=((90, 150, 220), (250, 220, 170)), hill=((130, 170, 150), (96, 140, 120)), orb=(255, 250, 200), orb_pos=(60, 60),
         stars=False, plank=(176, 120, 70), grass=(90, 180, 70)),
    dict(sky=((30, 14, 40), (150, 50, 70)), hill=((84, 30, 60), (56, 20, 48)), orb=(255, 190, 120), orb_pos=(250, 120),
         stars=True, plank=(140, 86, 60), grass=(130, 150, 60)),
    dict(sky=((8, 8, 24), (50, 50, 100)), hill=((30, 30, 70), (20, 20, 50)), orb=(240, 240, 255), orb_pos=(90, 46),
         stars=True, plank=(110, 92, 120), grass=(70, 120, 110)),
    dict(sky=((120, 170, 230), (255, 236, 190)), hill=((150, 190, 140), (110, 160, 110)), orb=(255, 244, 170), orb_pos=(256, 56),
         stars=False, plank=(190, 130, 76), grass=(110, 190, 80)),
    dict(sky=((24, 6, 30), (110, 30, 90)), hill=((70, 24, 80), (46, 14, 58)), orb=(255, 120, 150), orb_pos=(150, 70),
         stars=True, plank=(130, 80, 90), grass=(150, 90, 130)),
    dict(sky=((40, 4, 8), (190, 60, 30)), hill=((90, 24, 30), (60, 14, 22)), orb=(255, 90, 60), orb_pos=(160, 60),
         stars=False, plank=(120, 70, 50), grass=(160, 70, 40)),
]
