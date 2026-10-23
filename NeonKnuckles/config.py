"""Constants, characters, enemies, stages and tuning for Neon Knuckles."""
import os

TITLE = "Neon Knuckles"
W, H = 320, 224          # Mega Drive / Genesis low-res mode
FPS = 60
HUD_H = 30
FLOOR_Y = 150            # screen y of the back edge of the walkable street (depth z = 0)
DEPTH = 62               # walkable depth in pixels; feet screen y = FLOOR_Y + z - height

SAVE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "NeonKnuckles")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")

# --- player ----------------------------------------------------------------
PLAYER_HP = 64
GRAVITY = 760.0
JUMP_V = 250.0
START_LIVES = 3
EXTRA_LIFE_EVERY = 30000
Z_HIT = 9                # depth tolerance for melee hits

PLAYERS = {
    "kai":  dict(name="KAI", speed=62.0, power=1.1, color=(236, 72, 72)),
    "vera": dict(name="VERA", speed=70.0, power=0.95, color=(90, 170, 255)),
}

# Player attacks. rect = (x0, x1, y0, y1) relative to the feet, facing right, y negative = up.
#   t = (windup end, active end, total)   lunge = forward speed while active
ATTACKS = {
    "jab":    dict(poses=("punch_w", "punch"), rect=(4, 25, -38, -27), dmg=3, t=(0.05, 0.12, 0.20), sfx="punch"),
    "cross":  dict(poses=("punch_w", "cross"), rect=(4, 26, -38, -27), dmg=3, t=(0.05, 0.12, 0.21), sfx="punch"),
    "upper":  dict(poses=("upper_w", "upper"), rect=(2, 22, -52, -26), dmg=6, t=(0.09, 0.20, 0.38), kd=True,
                   lunge=30, sfx="hit"),
    "kick":   dict(poses=("kick_w", "kick"), rect=(6, 30, -40, -24), dmg=5, t=(0.10, 0.21, 0.36), sfx="kick"),
    "rkick":  dict(poses=("kick_w", "rkick"), rect=(6, 32, -46, -26), dmg=6, t=(0.11, 0.23, 0.42), kd=True,
                   sfx="hit"),
    "elbow":  dict(poses=("idle", "elbow"), rect=(-24, -2, -40, -26), dmg=6, t=(0.06, 0.17, 0.32), kd=True,
                   sfx="hit"),
    "spin":   dict(poses=("crouch", "spin"), rect=(-30, 30, -40, -10), dmg=7, t=(0.05, 0.45, 0.55), kd=True,
                   sfx="hit", cost=4),
    "jkick":  dict(poses=("jkick", "jkick"), rect=(4, 28, -34, -12), dmg=7, t=(0.0, 9.0, 9.0), kd=True, sfx="hit"),
    "knee":   dict(poses=("knee", "knee"), rect=(0, 22, -40, -10), dmg=4, t=(0.04, 0.12, 0.24), sfx="punch"),
    "swing":  dict(poses=("swing_w", "swing"), rect=(4, 36, -48, -16), dmg=8, t=(0.14, 0.26, 0.42), kd=True,
                   sfx="bat"),
    "stab":   dict(poses=("stab_w", "stab"), rect=(4, 30, -38, -26), dmg=6, t=(0.06, 0.15, 0.26), sfx="slash"),
    "toss":   dict(poses=("lift", "toss"), rect=None, dmg=0, t=(0.12, 0.13, 0.32)),
}
PUNCH_CHAIN = ("jab", "cross", "upper")
KICK_CHAIN = ("kick", "rkick")

# Weapons and pickups. uses = hits before a melee weapon breaks.
ITEMS = {
    "bat":     dict(kind="melee", uses=10, attack="swing", dmg=8),
    "pipe":    dict(kind="melee", uses=14, attack="swing", dmg=9),
    "knife":   dict(kind="throw", dmg=9),
    "crate":   dict(kind="heavy", dmg=12),
    "barrel":  dict(kind="heavy", dmg=12),
    "chicken": dict(kind="food", heal=32),
    "soda":    dict(kind="food", heal=14),
    "cash":    dict(kind="cash", pts=1000),
}

DIFFICULTIES = ["EASY", "NORMAL", "HARD"]
DIFF_TUNING = [dict(hp=0.8, dmg=0.7, attackers=1, cool=1.25),
               dict(hp=1.0, dmg=1.0, attackers=2, cool=1.0),
               dict(hp=1.25, dmg=1.3, attackers=3, cool=0.8)]


# --- characters --------------------------------------------------------------
def pal(**kw):
    base = dict(skin=(236, 184, 138), hair=(34, 24, 28), top=(210, 210, 220), top2=(240, 240, 240),
                pants=(60, 64, 96), shoe=(40, 32, 36), belt=(60, 44, 40), accent=(230, 60, 60),
                metal=(200, 210, 220))
    base.update(kw)
    return base


CHARS = {
    "kai":   dict(pal=pal(top=(200, 44, 52), top2=(236, 232, 220), pants=(54, 66, 120), shoe=(230, 230, 230),
                          hair=(40, 26, 22), accent=(250, 210, 80)), ex=("jacket", "spiky"), scale=1.0),
    "vera":  dict(pal=pal(skin=(244, 198, 160), top=(46, 120, 210), top2=(30, 30, 40), pants=(30, 30, 44),
                          shoe=(220, 60, 90), hair=(230, 190, 80), accent=(255, 255, 255)),
                  ex=("vest", "ponytail", "band"), scale=0.96),
    "punk":  dict(pal=pal(skin=(220, 170, 126), hair=(40, 210, 120), top=(70, 70, 82), top2=(70, 70, 82),
                          pants=(40, 44, 70), shoe=(30, 26, 30)), ex=("vest", "mohawk"), scale=1.0),
    "punk2": dict(pal=pal(skin=(196, 140, 100), hair=(30, 24, 24), top=(160, 120, 40), top2=(220, 210, 180),
                          pants=(90, 80, 70), shoe=(60, 40, 30)), ex=("jacket", "cap"), scale=1.0),
    "brawler": dict(pal=pal(skin=(210, 160, 120), hair=(40, 30, 26), top=(150, 40, 40), pants=(70, 60, 54),
                            shoe=(40, 30, 28), belt=(170, 130, 60)), ex=("bare", "bald", "beard"), scale=1.12),
    "knifer": dict(pal=pal(skin=(226, 180, 140), hair=(20, 18, 24), top=(30, 30, 36), top2=(180, 30, 40),
                           pants=(30, 30, 36), shoe=(20, 20, 24)), ex=("jacket", "shades", "long"), scale=1.0),
    "chain": dict(pal=pal(skin=(238, 190, 156), hair=(200, 40, 110), top=(120, 40, 140), top2=(30, 20, 30),
                          pants=(40, 26, 50), shoe=(30, 20, 30), metal=(170, 176, 190)),
                  ex=("vest", "ponytail", "shades"), scale=0.96),
    "hulk":  dict(pal=pal(skin=(170, 120, 90), hair=(30, 26, 24), top=(60, 90, 60), pants=(50, 54, 40),
                          shoe=(40, 36, 30), belt=(120, 100, 60)), ex=("bare", "bald", "pads"), scale=1.32),
    # bosses
    "tank":  dict(pal=pal(skin=(206, 150, 110), hair=(26, 20, 20), top=(80, 80, 92), pants=(46, 52, 70),
                          shoe=(30, 30, 34), belt=(200, 170, 60)), ex=("bare", "mohawk", "pads", "beard"),
                  scale=1.42),
    "razor": dict(pal=pal(skin=(232, 196, 160), hair=(236, 236, 240), top=(236, 236, 240), top2=(30, 30, 40),
                          pants=(36, 36, 44), shoe=(20, 20, 24)), ex=("jacket", "spiky", "shades"), scale=1.05),
    "mamba": dict(pal=pal(skin=(214, 160, 120), hair=(20, 16, 20), top=(30, 140, 80), top2=(20, 30, 20),
                          pants=(20, 60, 40), shoe=(20, 20, 20), metal=(220, 200, 120)),
                  ex=("vest", "long", "band"), scale=1.02),
    "viper": dict(pal=pal(skin=(220, 176, 140), hair=(20, 16, 22), top=(120, 20, 30), top2=(240, 200, 80),
                          pants=(26, 20, 26), shoe=(20, 16, 18), metal=(230, 236, 250)),
                  ex=("coat", "long", "beard"), scale=1.12),
    "tomo":  dict(pal=pal(skin=(244, 200, 164), hair=(230, 190, 80), top=(250, 180, 60), pants=(60, 90, 160),
                          shoe=(220, 220, 220)), ex=("cap",), scale=0.78),
}

# --- enemies -----------------------------------------------------------------
# moves: (move, weight, min |dx|, max |dx|). Bosses use the same move system with armour in wind-ups.
ENEMIES = {
    "punk":    dict(char="punk", name="SPIKE", hp=16, speed=46, score=200, grab=True,
                    moves=[("jab", 5, 0, 30), ("kick", 3, 0, 34)]),
    "punk2":   dict(char="punk2", name="DUKE", hp=18, speed=50, score=250, grab=True,
                    moves=[("jab", 4, 0, 30), ("kick", 4, 0, 34), ("lunge", 2, 30, 70)]),
    "punk_bat": dict(char="punk2", name="DUKE", hp=18, speed=48, score=300, grab=True, weapon="bat",
                     moves=[("bat", 6, 0, 40)]),
    "punk_pipe": dict(char="punk", name="SPIKE", hp=18, speed=46, score=300, grab=True, weapon="pipe",
                      moves=[("bat", 6, 0, 42)]),
    "brawler": dict(char="brawler", name="BRUNO", hp=30, speed=38, score=450, grab=True,
                    moves=[("grab", 4, 0, 22), ("headbutt", 3, 0, 26), ("slam", 3, 0, 32)]),
    "knifer":  dict(char="knifer", name="SLICK", hp=18, speed=52, score=350, grab=True, weapon="knife",
                    ranged=(80, 150), moves=[("throwknife", 5, 70, 200), ("slash", 4, 0, 30)]),
    "chain":   dict(char="chain", name="LASH", hp=22, speed=56, score=400, grab=True, weapon="chain",
                    moves=[("whip", 6, 16, 52), ("kick", 2, 0, 32), ("flip", 1, 0, 30)]),
    "hulk":    dict(char="hulk", name="BOULDER", hp=50, speed=34, score=900, grab=False,
                    moves=[("charge", 3, 60, 220), ("slam", 4, 0, 36), ("grab", 2, 0, 24)]),
    # bosses
    "tank":    dict(char="tank", name="TANK", title="BOSS OF NEON ROW", hp=90, speed=40, score=5000, grab=False,
                    boss=True, block=0.12, quote="NOBODY WALKS ON MY STREET.",
                    moves=[("charge", 4, 70, 260), ("slam", 5, 0, 38), ("grab", 3, 0, 26), ("stomp", 2, 0, 400)]),
    "razor":   dict(char="razor", name="RAZOR", title="THE DOCK BUTCHER", hp=80, speed=72, score=6000, grab=False,
                    boss=True, block=0.3, weapon="knife", quote="I'LL CARVE MY NAME IN YOU.",
                    moves=[("dashslash", 5, 50, 220), ("fan", 4, 90, 400), ("slash3", 4, 0, 34),
                           ("jumpstab", 3, 40, 180), ("flip", 2, 0, 40)]),
    "mamba":   dict(char="mamba", name="MAMBA", title="QUEEN OF THE IRONWORKS", hp=86, speed=66, score=7000,
                    grab=False, boss=True, block=0.25, weapon="chain", quote="DANCE FOR ME, LITTLE FIGHTER.",
                    moves=[("whip", 5, 18, 56), ("spinwhip", 3, 0, 46), ("flip", 3, 0, 34),
                           ("whip2", 4, 20, 58), ("dashslash", 2, 70, 200)]),
    "viper":   dict(char="viper", name="VIPER", title="HEAD OF THE IRON SERPENTS", hp=130, speed=70, score=15000,
                    grab=False, boss=True, block=0.35, weapon="katana", summon="punk",
                    quote="YOU CAME ALL THIS WAY TO DIE ON MY FLOOR.",
                    moves=[("katana", 5, 0, 44), ("dashslash", 4, 60, 240), ("stars", 3, 90, 400),
                           ("katana3", 3, 0, 40), ("jumpstab", 2, 50, 180), ("flip", 2, 0, 36)]),
}

# --- stages ------------------------------------------------------------------
# waves: (camera lock x, [(enemy, side, delay), ...], boss_wave)
#   side: "L" / "R" = walk in from that screen edge.
# items: (kind, x, z)   hazards: ("water", x0, x1) front edge of the pier, ("vent", x, z) steam vent
STAGES = [
    dict(name="NEON ROW", sub="DOWNTOWN - 11:40 PM", theme="neon", length=1640, time=200, music="street",
         waves=[(0, [("punk", "R", 0.6), ("punk", "R", 2.2), ("punk", "L", 4.0)], False),
                (340, [("punk2", "R", 0.0), ("punk_bat", "R", 1.0), ("punk", "L", 2.5)], False),
                (680, [("brawler", "R", 0.0), ("punk", "R", 1.6), ("punk2", "L", 3.0)], False),
                (1020, [("punk_bat", "L", 0.0), ("brawler", "R", 0.5), ("punk2", "R", 2.0), ("punk", "R", 4)],
                 False),
                (1320, [("tank", "R", 0.6), ("punk", "L", 7.0), ("punk2", "R", 14.0)], True)],
         items=[("crate", 250, 10), ("soda", 600, 40), ("barrel", 920, 8), ("chicken", 1240, 30)],
         hazards=[]),
    dict(name="RUSTWATER DOCKS", sub="PIER 9 - 3:15 AM", theme="docks", length=1900, time=220, music="street",
         waves=[(0, [("knifer", "R", 0.6), ("punk", "R", 1.5), ("punk2", "L", 3.0)], False),
                (380, [("punk_pipe", "R", 0.0), ("knifer", "R", 1.2), ("brawler", "L", 2.4)], False),
                (760, [("hulk", "R", 0.2), ("punk", "L", 1.5), ("knifer", "R", 3.0)], False),
                (1150, [("knifer", "R", 0.0), ("knifer", "L", 0.8), ("brawler", "R", 2.0), ("punk_bat", "R", 3)],
                 False),
                (1580, [("razor", "R", 0.6), ("knifer", "L", 9.0), ("punk2", "R", 16.0)], True)],
         items=[("crate", 300, 6), ("knife", 520, 30), ("crate", 980, 10), ("chicken", 1340, 20),
                ("barrel", 1420, 8)],
         hazards=[("water", 470, 650), ("water", 1020, 1240)]),
    dict(name="THE IRONWORKS", sub="SMELTER NO. 4 - 4:50 AM", theme="factory", length=2000, time=230,
         music="factory",
         waves=[(0, [("chain", "R", 0.5), ("punk2", "R", 1.6), ("punk", "L", 2.8)], False),
                (400, [("chain", "R", 0.0), ("brawler", "R", 1.0), ("punk_pipe", "L", 2.0)], False),
                (800, [("hulk", "R", 0.0), ("chain", "L", 1.0), ("knifer", "R", 2.5)], False),
                (1220, [("hulk", "L", 0.0), ("chain", "R", 0.6), ("punk_bat", "R", 1.8), ("knifer", "L", 3.0)],
                 False),
                (1680, [("mamba", "R", 0.6), ("chain", "L", 8.0), ("punk_pipe", "R", 15.0)], True)],
         items=[("pipe", 280, 40), ("soda", 640, 20), ("barrel", 1000, 12), ("chicken", 1480, 30)],
         hazards=[("vent", 520, 20), ("vent", 600, 46), ("vent", 1060, 30), ("vent", 1400, 14),
                  ("vent", 1460, 48), ("vent", 1880, 36)]),
    dict(name="SERPENT TOWER", sub="TOP FLOOR - 5:59 AM", theme="tower", length=1900, time=240, music="final",
         waves=[(0, [("punk", "R", 0.4), ("chain", "R", 1.2), ("knifer", "L", 2.0), ("punk2", "R", 3.0)], False),
                (380, [("hulk", "R", 0.0), ("brawler", "L", 0.8), ("punk_bat", "R", 2.0)], False),
                (760, [("tank", "R", 0.4), ("punk", "L", 6.0)], False),
                (1120, [("razor", "R", 0.4), ("mamba", "L", 1.0)], False),
                (1580, [("viper", "R", 0.8)], True)],
         items=[("chicken", 360, 30), ("crate", 700, 8), ("soda", 1060, 40), ("chicken", 1500, 20),
                ("bat", 1200, 50)],
         hazards=[]),
]

# Mid-stage rematches use weaker copies of the bosses.
REMATCH_HP = 0.6

THEMES = {
    "neon":    dict(sky=((14, 6, 40), (120, 30, 110)), far=(30, 20, 70), win=(255, 220, 120)),
    "docks":   dict(sky=((14, 18, 54), (230, 110, 70)), far=(40, 34, 70), win=(255, 200, 120)),
    "factory": dict(sky=((20, 14, 16), (90, 40, 24)), far=(46, 30, 28), win=(255, 140, 50)),
    "tower":   dict(sky=((6, 6, 22), (40, 30, 90)), far=(24, 20, 50), win=(255, 230, 150)),
}
