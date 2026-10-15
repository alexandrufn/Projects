"""Game-wide constants, visual themes, characters and the CPU bounty ladder."""
import os

TITLE = "High Noon: Reloaded"

# Logical (pixel-art) resolution. The window is scaled up with pygame.SCALED.
W, H = 400, 225
FPS = 60

HUD_H = 20
HORIZON = 56          # where the sky meets the ground
BULLET_MIN_Y = 66     # top fence: bullets ricochet here
BULLET_MAX_Y = 219    # bottom fence
PLAYER_MIN_Y = 88     # feet y limits
PLAYER_MAX_Y = 218
LEFT_ZONE = (12, 128)
RIGHT_ZONE = (272, 388)

PLAYER_SPEED = 72.0
BULLET_SPEED = 235.0
AIM_ANGLES = {"up": -0.40, "straight": 0.0, "down": 0.40}
GUN_OFFSETS = {"up": (8, -13), "straight": (9, -12), "down": (9, -10)}
CYLINDER = 6
RELOAD_TIME = 1.5
FIRE_COOLDOWN = 0.30
JAM_TIME = 1.0
ROUND_TIME = 45.0
POINTS_CPU = 3
POINTS_PVP = 5

SAVE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HighNoonReloaded")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")


# ----------------------------------------------------------------------------
# Times of day
# ----------------------------------------------------------------------------
THEMES = {
    "morning": dict(sky=((118, 168, 228), (252, 214, 168)), sun=(255, 244, 200), sun_pos=(64, 40), sun_r=8,
                    far=(196, 150, 150), near=(170, 110, 92), town=(120, 74, 64),
                    ground=((226, 188, 128), (206, 154, 96)), fence=(124, 80, 46),
                    cloud=(255, 246, 236), tint=None),
    "noon": dict(sky=((60, 128, 226), (168, 210, 246)), sun=(255, 255, 230), sun_pos=(330, 28), sun_r=8,
                 far=(200, 160, 128), near=(178, 116, 78), town=(130, 80, 58),
                 ground=((238, 204, 138), (220, 170, 100)), fence=(130, 84, 48),
                 cloud=(255, 255, 255), tint=None),
    "afternoon": dict(sky=((86, 142, 214), (240, 198, 150)), sun=(255, 232, 168), sun_pos=(300, 34), sun_r=9,
                      far=(190, 140, 120), near=(160, 100, 72), town=(112, 68, 52),
                      ground=((228, 180, 116), (204, 146, 86)), fence=(122, 78, 44),
                      cloud=(255, 236, 214), tint=(255, 246, 232)),
    "dust": dict(sky=((190, 140, 92), (232, 186, 120)), sun=(255, 226, 170), sun_pos=(90, 30), sun_r=7,
                 far=(200, 156, 110), near=(176, 120, 80), town=(140, 96, 66),
                 ground=((214, 168, 108), (190, 140, 84)), fence=(120, 80, 48),
                 cloud=None, tint=(255, 232, 196), dust=True),
    "sunset": dict(sky=((70, 44, 112), (252, 134, 62)), sun=(255, 190, 90), sun_pos=(290, 54), sun_r=14,
                   far=(150, 74, 92), near=(96, 46, 60), town=(64, 30, 44),
                   ground=((206, 124, 82), (170, 92, 62)), fence=(96, 52, 36),
                   cloud=(250, 170, 140), tint=(255, 212, 184)),
    "dusk": dict(sky=((22, 24, 70), (196, 88, 96)), moon=(240, 236, 220), sun_pos=(330, 22), sun_r=5,
                 far=(90, 56, 96), near=(58, 36, 66), town=(36, 22, 44),
                 ground=((130, 92, 96), (104, 72, 82)), fence=(70, 44, 46),
                 cloud=(150, 90, 120), tint=(196, 170, 206), stars=True, lights=True),
    "night": dict(sky=((4, 8, 26), (30, 44, 92)), moon=(232, 236, 255), sun_pos=(80, 26), sun_r=7,
                  far=(40, 48, 86), near=(26, 30, 60), town=(14, 16, 36),
                  ground=((60, 64, 100), (44, 46, 78)), fence=(40, 36, 52),
                  cloud=None, tint=(120, 132, 190), stars=True, lights=True),
}


# ----------------------------------------------------------------------------
# Characters (palette letters match the sprite rows in gfx.py)
# ----------------------------------------------------------------------------
def _char(name, hat, band, skin, hair, scarf, shirt, vest, pants, boots, gun=(176, 176, 188)):
    return {"name": name, "colors": dict(
        H=hat, h=band, S=skin, M=hair, N=scarf, C=shirt, V=vest, P=pants, K=boots, G=gun,
        B=(70, 42, 26), b=(250, 210, 90), E=(28, 18, 18))}


SHERIFF = _char("SHERIFF COLE", (200, 155, 95), (95, 55, 30), (238, 188, 140), (120, 75, 40),
                (60, 110, 190), (235, 230, 215), (130, 85, 45), (70, 85, 120), (95, 58, 32))
# Miss Lily, rescued from El Diablo (ending only). Gun colour matches the dress: she's unarmed.
GIRL = dict(_char("MISS LILY", (0, 0, 0), (230, 70, 110), (244, 200, 166), (236, 190, 90),
                  (250, 250, 250), (250, 246, 236), (120, 170, 220), (150, 196, 236), (130, 80, 60),
                  gun=(150, 196, 236)), body="girl")
OUTLAW = _char("BLACK JACK", (45, 40, 48), (160, 35, 35), (225, 170, 125), (40, 30, 30),
               (170, 40, 40), (150, 45, 45), (50, 42, 48), (100, 75, 55), (40, 32, 30))

# Cover layouts: (kind, x, base_y[, speed]). "tumble" entries roll in with the wind.
LAYOUTS = [
    [("cactus", 170, 122), ("cactus", 232, 192), ("rock", 200, 160)],
    [("wagon", 200, 152), ("cactus", 160, 104), ("cactus", 242, 208)],
    [("barrel", 166, 112), ("barrel", 236, 142), ("barrel", 180, 202), ("cactus", 216, 176), ("tumble", 0, 0)],
    [("coach", 200, 126, 26), ("cactus", 160, 204), ("cactus", 246, 98)],
    [("cactus", 160, 106), ("cactus", 200, 152), ("cactus", 240, 204), ("barrel", 226, 116),
     ("barrel", 174, 186), ("tumble", 0, 0), ("tumble", 0, 0)],
    [("coach", 186, 150, 40), ("barrel", 242, 102), ("barrel", 242, 204), ("rock", 158, 112), ("rock", 158, 196)],
    [("cactus", 200, 142), ("tumble", 0, 0), ("tumble", 0, 0)],
]

DIFFICULTY = ["GREENHORN", "EASY", "FAIR", "TOUGH", "HARD", "DEADLY", "LEGENDARY"]

# CPU ladder. Lower reaction/aim_err/interval = deadlier.
#   reaction : seconds of perception lag      aim_err : px of aiming noise
#   speed    : movement multiplier             dodge   : chance to dodge a bullet
#   interval : min seconds between shots       draw    : quick-draw delay after "DRAW!"
#   ricochet : plans bank shots off fences     predict : leads a moving target
#   cover    : hides behind cover to reload    strafe  : jitter to be hard to hit
LEVELS = [
    dict(char=_char("DUSTY PETE", (150, 120, 80), (90, 70, 50), (232, 180, 140), (190, 190, 180),
                    (200, 170, 80), (170, 150, 100), (110, 90, 60), (120, 100, 70), (80, 60, 40)),
         title="CATTLE RUSTLER", bounty=50, theme="morning", layout=0,
         quote="THEM COWS WAS ALREADY LOST, HONEST.",
         reaction=0.90, aim_err=18, speed=0.55, dodge=0.00, interval=1.6, draw=1.4,
         ricochet=False, predict=False, cover=False, strafe=0.0, aggression=0.2),
    dict(char=_char("SLIM JIM", (90, 90, 104), (200, 200, 210), (236, 196, 160), (60, 50, 40),
                    (120, 40, 120), (220, 220, 232), (60, 60, 96), (60, 60, 70), (30, 28, 30)),
         title="CARD SHARP", bounty=100, theme="noon", layout=1,
         quote="READ 'EM AND WEEP, PARTNER.",
         reaction=0.75, aim_err=14, speed=0.65, dodge=0.10, interval=1.3, draw=1.1,
         ricochet=False, predict=False, cover=False, strafe=0.0, aggression=0.35),
    dict(char=_char("MAD DOG MCGRAW", (110, 70, 40), (40, 30, 20), (220, 160, 120), (150, 60, 30),
                    (200, 40, 30), (90, 130, 80), (80, 50, 30), (90, 80, 60), (60, 40, 25)),
         title="BANK ROBBER", bounty=250, theme="afternoon", layout=2,
         quote="I AIN'T MAD. I'M JUST MCGRAW.",
         reaction=0.60, aim_err=11, speed=0.75, dodge=0.20, interval=1.05, draw=0.9,
         ricochet=False, predict=False, cover=False, strafe=0.1, aggression=0.75),
    dict(char=_char("BLACK BART", (30, 28, 34), (90, 90, 96), (210, 160, 120), (30, 26, 26),
                    (30, 28, 34), (80, 80, 88), (40, 36, 42), (54, 50, 56), (26, 22, 22)),
         title="STAGECOACH BANDIT", bounty=500, theme="dust", layout=3,
         quote="NOBODY SEES BART COMIN' THROUGH THE DUST.",
         reaction=0.48, aim_err=8, speed=0.85, dodge=0.30, interval=0.9, draw=0.7,
         ricochet=True, predict=False, cover=True, strafe=0.2, aggression=0.45),
    dict(char=dict(_char("TWO-GUN ROSA", (190, 60, 60), (250, 210, 90), (226, 164, 120), (58, 28, 20),
                         (40, 120, 90), (244, 228, 200), (150, 30, 50), (120, 60, 70), (80, 36, 28)),
                   body="lady", hp=2, twin=True),
         title="QUEEN OF THE DESPERADOS", bounty=1000, theme="sunset", layout=4, boss=True,
         quote="TWO GUNS. ONE OF YOU. BAD ODDS, AMIGO.",
         boss_note="BOSS: TAKES 2 HITS A ROUND AND FIRES BOTH GUNS AT ONCE",
         reaction=0.38, aim_err=6, speed=0.92, dodge=0.40, interval=0.75, draw=0.55,
         ricochet=True, predict=True, cover=False, strafe=0.3, aggression=0.6),
    dict(char=dict(_char("THE UNDERTAKER", (28, 28, 32), (120, 120, 130), (220, 212, 204), (80, 80, 84),
                         (230, 230, 230), (34, 32, 38), (20, 20, 24), (32, 30, 36), (18, 16, 18)),
                   body="mounted", hp=2,
                   horse=dict(body=(44, 40, 46), mane=(18, 16, 20), blanket=(120, 30, 40))),
         title="HIRED GUN", bounty=2500, theme="dusk", layout=5, boss=True,
         quote="I ALWAYS BRING A SPARE BOX. YOUR SIZE.",
         boss_note="BOSS: ON HORSEBACK - 2 HITS A ROUND, THE HORSE COUNTS",
         reaction=0.24, aim_err=3, speed=1.1, dodge=0.50, interval=0.58, draw=0.40,
         ricochet=True, predict=True, cover=True, strafe=0.4, aggression=0.4),
    dict(char=dict(_char("EL DIABLO", (120, 20, 25), (250, 200, 60), (200, 92, 76), (24, 12, 12),
                         (230, 180, 60), (40, 20, 25), (34, 24, 28), (40, 30, 35), (20, 12, 12)),
                   body="brute", hp=3),
         title="THE DEVIL HIMSELF", bounty=10000, theme="night", layout=6, boss=True,
         quote="MIDNIGHT'S MY HOUR. NOON WAS YOURS.",
         boss_note="FINAL BOSS: TAKES 3 HITS A ROUND AND GETS ANGRIER",
         reaction=0.18, aim_err=2.5, speed=1.05, dodge=0.65, interval=0.45, draw=0.28,
         ricochet=True, predict=True, cover=True, strafe=0.5, aggression=0.55),
]
