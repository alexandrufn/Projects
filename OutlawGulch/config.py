"""Game-wide constants for Outlaw Gulch."""
import os

TITLE = "Outlaw Gulch"

# Logical (pixel-art) resolution. The window is scaled up with pygame.SCALED.
W, H = 320, 256
FPS = 60
OY = 16                       # top of the play field (HUD above)
PLAY_H = H - OY

SCROLL_SPEED = 34.0           # px/s the world scrolls while a stage is under way
PLAYER_SPEED = 86.0
PLAYER_HP = 3
LIVES = 3
START_BOMBS = 1
MAX_BOMBS = 3
INVULN_HIT = 1.3
INVULN_RESPAWN = 2.2

BOUNTY_EXTRA_LIFE = 20000

SAVE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "OutlawGulch")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")

# Playable heroes: original 80s action-hero archetypes with different strengths.
HEROES = {
    "hank": dict(name="HEADBAND HANK", tag="Fast, fierce, bare-handed tough guy",
                 speed=1.12, cd=0.85, hp=3, max_hp=5, bombs=1, pips=(5, 5, 3, 1)),
    "carl": dict(name="COMMANDO CARL", tag="Slow, tough, comes loaded with bombs",
                 speed=0.94, cd=1.0, hp=4, max_hp=6, bombs=2, pips=(3, 3, 4, 2)),
}
HERO_ORDER = ("hank", "carl")

# Weapons: cooldown (s), bullet speed, damage, pierce, pellets, spread (rad), lifetime (s)
WEAPONS = {
    "revolver": dict(cd=0.20, speed=270.0, dmg=1, pierce=False, pellets=1, spread=0.0, life=2.0),
    "shotgun": dict(cd=0.46, speed=240.0, dmg=1, pierce=False, pellets=5, spread=0.55, life=0.42),
    "rifle": dict(cd=0.13, speed=340.0, dmg=1, pierce=True, pellets=1, spread=0.0, life=2.0),
}
WEAPON_TIME = 22.0

STAGES = [
    dict(name="DUSTY TOWN", length=1700, theme=0, density=1.0,
         boss="ONE-EYED JACK", reward=5000, hp=50, kind="jack"),
    dict(name="CANYON PASS", length=1900, theme=1, density=1.2,
         boss="LOLA LA LOCA", reward=8000, hp=65, kind="lola"),
    dict(name="RAIL YARD", length=2100, theme=2, density=1.35,
         boss="IRON MIKE", reward=12000, hp=85, kind="mike"),
    dict(name="SILVER MINE", length=2300, theme=3, density=1.5,
         boss="EL COBRA", reward=16000, hp=100, kind="cobra"),
    dict(name="HACIENDA", length=2500, theme=4, density=1.65,
         boss="GENERAL DIABLO", reward=25000, hp=130, kind="diablo"),
]
