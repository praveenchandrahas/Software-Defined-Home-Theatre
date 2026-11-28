"""The film's single timeline: every time, position and level that picture and sound share. Times in seconds.

Coordinates are from the seat: x to the right, y forward, z up (as in Spatial-Lab)."""
import math

FPS = 24
DUR = 100.0
FS = 48000

# Speaker directions from the seat (the measured layout used by Spatial-Lab and film I).
SPEAKERS = {
    "FL": (-0.437, 0.896, 0.085), "FR": (0.436, 0.894, 0.099),
    "TFL": (-0.345, 0.458, 0.819), "TFR": (0.374, 0.555, 0.743),
    "C": (0.0, 0.995, 0.103),
    "SL": (-0.812, -0.536, 0.230), "SR": (0.858, -0.472, 0.203),
}
VBAP_ORDER = ["FL", "FR", "TFL", "TFR", "C", "SL", "SR"]
FILE_ORDER = ["FL", "FR", "C", "LFE", "TFL", "TFR", "SL", "SR"]       # 7.1 order; heights ride in BL/BR

# Rendered scenes: (start, end, engine for the animatic)
SCENES = {
    "echo": (8.0, 18.0, "eevee"),
    "storm": (30.0, 42.0, "eevee"),
    "drop": (42.0, 50.0, "eevee"),
    "canyon": (50.0, 65.0, "cycles"),
    "earth": (65.0, 75.0, "cycles"),
    "shatter": (78.0, 90.0, "eevee"),
    "title": (90.0, 100.0, "eevee"),
}
# Stock: (name, Pexels id, film start, film end, in-point in the clip)
STOCK = [("water", 16392053, 18.0, 30.0, 4.0)]

# 0-8 s: black
TICK_L = 3.0
AIR = (4.0, 8.6)
# 8-18 s: echoes. Each ping comes from a speaker; the wave is drawn 100x slower than sound.
PINGS = [(8.6, "C"), (10.9, "FL"), (12.9, "FR"), (14.6, "TFL"), (16.2, "SR")]
WAVE_SPEED = 3.43                               # metres per second on screen
ROOM = dict(width=3.0, depth=3.4, height=2.7, seat=(0.0, 0.0, 1.05), front=2.4)   # front wall 2.4 m ahead
SPEAKER_DIST = 2.2                              # metres from the seat, for drawing the ping sources
# 18-30 s: rain (stock water), building to a downpour
RAIN = (18.0, 36.0)
# 30-42 s: storm. Strikes: (time, azimuth deg, elevation deg); thunder rolls towards the back after each.
STRIKES = [(31.0, -30, 38), (33.4, 28, 52), (36.0, -58, 30), (38.7, 5, 68), (40.6, 42, 34)]
CUT_TO_BLACK = 42.0                             # picture and sound cut to nothing
# 42-50 s: one drop
DROP_FALL = (43.4, 46.0)
DROP_HIT = 46.0
# 50-65 s: canyon. Passes: (time of closest approach, side) with side L, R or UP.
CANYON_ENTRY = 50.0
PASSES = [(51.6, "L"), (53.0, "R"), (54.3, "UP"), (55.6, "L"), (56.8, "R"), (57.9, "UP"),
          (58.9, "L"), (59.7, "R"), (60.4, "UP"), (61.0, "L")]
PASS_SPEED = 60.0                               # metres per second, relative to the camera
PASS_OFFSET = {"L": (-2.6, 0.0, 0.3), "R": (2.6, 0.0, 0.2), "UP": (0.0, 0.0, 2.6)}
OPEN = (61.5, 64.0)                             # the frame grows from 2.39:1 to 16:9
SCOPE = 2.39
# 65-75 s: orbit
SUN_CREST = 70.0
FADE_OUT = (74.0, 75.0)
SILENCE = (75.0, 78.0)                          # digital zero
# 78-90 s: pressure wave
HIT = 78.0
THUMPS = [79.5 + 0.75 * k for k in range(12)]
# 90-100 s: title
TITLE_IN = (91.0, 93.5)
LIGHT_OUT = 98.0
TICK_R = 99.0


def frame_of(t):
    return int(round(t * FPS))


def scene_frame(name, t):
    """Frame number inside a scene's render (1-based) for film time t."""
    return int(round((t - SCENES[name][0]) * FPS)) + 1


def polar(az_deg, el_deg, r=1.0):
    az, el = math.radians(az_deg), math.radians(el_deg)
    return (r * math.sin(az) * math.cos(el), r * math.cos(az) * math.cos(el), r * math.sin(el))


def pass_pos(t, tp, side):
    """Position of a canyon pass relative to the camera at film time t."""
    ox, oy, oz = PASS_OFFSET[side]
    return (ox, oy - PASS_SPEED * (t - tp), oz)


def aspect(t):
    """Picture aspect ratio at time t: scope, then opening to 16:9."""
    a, b = OPEN
    if t <= a:
        return SCOPE
    if t >= b:
        return 16 / 9
    x = (t - a) / (b - a)
    x = x * x * (3 - 2 * x)
    return 1 / ((1 - x) / SCOPE + x * 9 / 16)
