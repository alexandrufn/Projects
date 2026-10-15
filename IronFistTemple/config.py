"""Constants, floor definitions, characters and boss tuning for Iron Fist Temple."""
import os

TITLE = "Iron Fist Temple"
W, H = 384, 216
FPS = 60
GROUND = 182            # feet y
HUD_H = 34

SAVE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "IronFistTemple")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")

# --- player ----------------------------------------------------------------
PLAYER_HP = 48
PLAYER_SPEED = 74.0
JUMP_V = 250.0
GRAVITY = 640.0
START_LIVES = 3
EXTRA_LIFE_EVERY = 25000

# Attack table. rect = (x0, x1, y0, y1) relative to feet, facing right, y negative = up.
#   t = (windup end, active end, total duration)
ATTACKS = {
    "punch":  dict(rect=(5, 25, -37, -28), dmg=1, t=(0.07, 0.18, 0.30), pts=100),
    "kick":   dict(rect=(6, 29, -42, -28), dmg=2, t=(0.12, 0.26, 0.42), pts=200),
    "cpunch": dict(rect=(5, 25, -22, -12), dmg=1, t=(0.07, 0.18, 0.30), pts=100),
    "ckick":  dict(rect=(5, 31, -9, 0),    dmg=2, t=(0.12, 0.28, 0.44), pts=200),
    "jkick":  dict(rect=(4, 26, -32, -14), dmg=3, t=(0.00, 9.00, 9.00), pts=300),
}

DIFFICULTIES = ["EASY", "NORMAL", "HARD"]
#                 boss hp  boss dmg  boss speed  enemy dmg
DIFF_TUNING = [dict(hp=0.75, dmg=0.7, spd=0.9, edmg=0.8),
               dict(hp=1.0, dmg=1.0, spd=1.0, edmg=1.0),
               dict(hp=1.3, dmg=1.25, spd=1.12, edmg=1.2)]

# --- floors ----------------------------------------------------------------
# pool: (enemy kind, weight)   hazards: ("pot"|"flame", count)
FLOORS = [
    dict(name="THE GATE OF EMBERS", length=1500, time=150, bg="ember", boss=0, gap=(80, 150),
         pool=[("grab", 6), ("knife", 3), ("imp", 2)], hazards=[]),
    dict(name="THE MOONLIT HALL", length=1650, time=155, bg="moon", boss=1, gap=(72, 140),
         pool=[("grab", 5), ("knife", 4), ("imp", 3), ("monk", 2)], hazards=[("pot", 6)]),
    dict(name="THE JADE CORRIDOR", length=1800, time=160, bg="jade", boss=2, gap=(66, 130),
         pool=[("grab", 4), ("knife", 3), ("imp", 3), ("monk", 3), ("snake", 5)], hazards=[]),
    dict(name="THE SPIRIT CHAMBER", length=1950, time=165, bg="spirit", boss=3, gap=(60, 120),
         pool=[("grab", 4), ("knife", 4), ("imp", 3), ("monk", 4), ("snake", 2)], hazards=[("flame", 5)]),
    dict(name="THE DRAGON THRONE", length=2100, time=175, bg="inferno", boss=4, gap=(54, 110),
         pool=[("grab", 4), ("knife", 4), ("imp", 4), ("monk", 5), ("snake", 3)],
         hazards=[("pot", 6), ("flame", 6)]),
]

BGS = {
    "ember":   dict(wall=((92, 40, 40), (150, 70, 52)), far=(120, 56, 52), pillar=(176, 40, 36), gold=(238, 188, 80),
                    glow=(255, 170, 70), floor=((120, 78, 58), (80, 50, 42)), sky=((60, 30, 70), (250, 140, 80)),
                    mood=None, motes=(255, 190, 110)),
    "moon":    dict(wall=((30, 40, 84), (60, 78, 130)), far=(44, 58, 110), pillar=(56, 76, 150), gold=(190, 210, 240),
                    glow=(150, 190, 255), floor=((74, 92, 130), (44, 56, 90)), sky=((10, 14, 50), (60, 90, 160)),
                    mood=(190, 205, 255), motes=(210, 230, 255)),
    "jade":    dict(wall=((26, 70, 56), (56, 118, 84)), far=(40, 94, 74), pillar=(40, 130, 90), gold=(230, 214, 130),
                    glow=(150, 255, 170), floor=((84, 112, 82), (50, 74, 56)), sky=((30, 70, 60), (170, 220, 150)),
                    mood=(215, 255, 215), motes=(170, 255, 170)),
    "spirit":  dict(wall=((52, 28, 84), (96, 54, 140)), far=(76, 44, 116), pillar=(110, 60, 170), gold=(214, 180, 255),
                    glow=(200, 120, 255), floor=((90, 64, 120), (56, 38, 84)), sky=((24, 10, 56), (120, 60, 160)),
                    mood=(235, 205, 255), motes=(225, 160, 255)),
    "inferno": dict(wall=((34, 12, 16), (90, 24, 26)), far=(70, 20, 24), pillar=(40, 30, 34), gold=(255, 200, 70),
                    glow=(255, 110, 40), floor=((70, 30, 30), (34, 14, 16)), sky=((20, 4, 8), (160, 40, 20)),
                    mood=(255, 200, 175), motes=(255, 120, 50)),
}


# --- characters ---------------------------------------------------------------
def pal(**kw):
    base = dict(skin=(238, 186, 140), hair=(30, 22, 26), band=None, gi=(220, 220, 230), pants=(60, 60, 80),
                belt=(220, 120, 40), shoe=(40, 30, 34), metal=(200, 210, 220), staff=(150, 100, 56),
                robe=None, cape=None, mask=None, bare=False)
    base.update(kw)
    return base


CHARS = {
    "hero": dict(pal=pal(gi=(58, 168, 164), pants=(236, 236, 240), belt=(236, 130, 40), band=(220, 40, 50),
                         shoe=(60, 40, 40)), ex=("band",), scale=1.0),
    "grab": dict(pal=pal(skin=(196, 170, 150), hair=(60, 50, 44), gi=(104, 90, 80), pants=(70, 62, 60),
                         belt=(150, 120, 80), bare=True, shoe=(50, 40, 36)), ex=("bald",), scale=1.0),
    "knife": dict(pal=pal(skin=(214, 170, 130), gi=(70, 58, 96), pants=(50, 44, 70), belt=(200, 60, 70),
                          mask=(50, 40, 72), shoe=(34, 28, 44)), ex=("mask", "bald", "band"), scale=1.0),
    "imp": dict(pal=pal(skin=(120, 180, 84), hair=(40, 70, 30), gi=(210, 70, 48), pants=(150, 40, 36),
                        belt=(240, 200, 80), shoe=(70, 30, 26)), ex=("horns", "bald"), scale=0.64),
    "monk": dict(pal=pal(skin=(226, 176, 128), gi=(234, 138, 34), pants=(160, 70, 28), belt=(120, 30, 40),
                         shoe=(70, 40, 30)), ex=("bald",), scale=1.0),
    "lotus": dict(pal=pal(skin=(244, 206, 172), hair=(24, 18, 28), gi=(236, 120, 160), pants=(236, 120, 160),
                          robe=(236, 120, 160), belt=(250, 230, 120), band=(250, 230, 120)),
                  ex=("robe", "ponytail", "band"), scale=1.0),
    # bosses
    "hu": dict(pal=pal(skin=(214, 164, 120), hair=(236, 236, 240), gi=(150, 56, 44), pants=(224, 208, 170),
                       belt=(240, 190, 70), band=(240, 190, 70), shoe=(70, 44, 34), staff=(176, 120, 62)),
               ex=("topknot", "beard", "band"), scale=1.1),
    "mei": dict(pal=pal(skin=(240, 196, 160), hair=(24, 18, 34), gi=(168, 52, 130), pants=(60, 40, 84),
                        belt=(240, 220, 120), band=(240, 220, 120), mask=(60, 40, 84), shoe=(40, 24, 50)),
                ex=("ponytail", "mask", "band", "blades"), scale=1.0),
    "gorr": dict(pal=pal(skin=(164, 160, 146), hair=(80, 76, 70), gi=(120, 116, 104), pants=(96, 72, 56),
                         belt=(236, 190, 70), bare=True, shoe=(60, 46, 40)), ex=("bald", "pads", "brow"),
                 scale=1.45),
    "sen": dict(pal=pal(skin=(214, 176, 150), hair=(236, 236, 250), gi=(70, 40, 130), pants=(70, 40, 130),
                        robe=(86, 50, 150), belt=(236, 200, 255), band=(214, 180, 255), shoe=(50, 30, 90)),
                ex=("robe", "beard", "hat", "band"), scale=1.05),
    "zhao": dict(pal=pal(skin=(196, 96, 78), hair=(22, 12, 16), gi=(40, 30, 44), pants=(30, 24, 36),
                         belt=(255, 200, 70), band=(255, 200, 70), cape=(150, 24, 40), shoe=(30, 20, 26),
                         bare=True),
                 ex=("horns", "cape", "pads", "bald"), scale=1.28),
}

# --- bosses ------------------------------------------------------------------
# moves: (name, weight, min_dist, max_dist). hp is in damage points (punch 1, kick 2, jump kick 3).
BOSSES = [
    dict(key="hu", name="MASTER HU", title="THE IRON STAFF", hp=26, speed=58, block=0.30, bonus=3000,
         quote="MY STAFF HAS BROKEN A HUNDRED SKULLS. YOURS IS NEXT.",
         moves=[("thrust", 5, 30, 90), ("spin", 3, 0, 60), ("leap", 3, 50, 160), ("thrust", 2, 0, 30)]),
    dict(key="mei", name="MEI THE TWIN BLADE", title="MISTRESS OF DISCS", hp=30, speed=84, block=0.30, bonus=4000,
         quote="TOO SLOW, LITTLE FIST. TOO SLOW.",
         moves=[("discs", 5, 70, 400), ("dash", 4, 40, 220), ("jumpslash", 3, 40, 200), ("slash", 3, 0, 50)]),
    dict(key="gorr", name="GORR THE STONE", title="THE MOUNTAIN THAT WALKS", hp=40, speed=44, block=0.15, bonus=5000,
         quote="STONE DOES NOT FEEL. STONE DOES NOT STOP.",
         moves=[("stomp", 4, 0, 400), ("charge", 4, 90, 400), ("swing", 5, 0, 60), ("stomp", 2, 0, 80)]),
    dict(key="sen", name="SEN THE SEER", title="WALKER OF SPIRIT PATHS", hp=36, speed=64, block=0.0, bonus=6000,
         quote="I SAW YOUR DEATH. I SAW IT THREE TIMES.",
         moves=[("fireballs", 5, 70, 400), ("teleport", 5, 0, 400), ("summon", 2, 0, 400), ("burst", 3, 0, 50)]),
    dict(key="zhao", name="ZHAO THE DRAGON LORD", title="MASTER OF THE TEMPLE", hp=60, speed=76, block=0.30,
         bonus=10000, quote="KNEEL, AND I WILL MAKE IT QUICK.",
         moves=[("dash", 4, 50, 240), ("flame", 3, 40, 160), ("stomp", 3, 0, 400), ("fireballs", 3, 80, 400),
                ("burst", 3, 0, 50), ("combo", 4, 0, 90), ("teleport", 2, 0, 400), ("summon", 1, 0, 400)]),
]
