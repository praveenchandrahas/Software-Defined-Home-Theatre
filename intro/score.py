"""The score: one description of where things are and when. Sound and picture both read it.

Room coordinates in metres from the seat: x right, y towards the screen, z up.
"""
import math
import numpy as np

FPS = 24
DUR = 60.0
FS = 48000

# Directions from the seat, the measured layout used by Spatial-Lab.
SPEAKERS = {
    "FL": (-0.437, 0.896, 0.085), "FR": (0.436, 0.894, 0.099),
    "TFL": (-0.345, 0.458, 0.819), "TFR": (0.374, 0.555, 0.743),
    "C": (0.0, 0.995, 0.103),
    "SL": (-0.812, -0.536, 0.230), "SR": (0.858, -0.472, 0.203),
}
VBAP_ORDER = ["FL", "FR", "TFL", "TFR", "C", "SL", "SR"]
# Standard 7.1 file order. The heights ride in BL/BR, which reach the interface's rear ports.
FILE_ORDER = ["FL", "FR", "C", "LFE", "TFL", "TFR", "SL", "SR"]


def smooth(a, b, t):
    x = np.clip((t - a) / (b - a), 0.0, 1.0)
    return x * x * (3 - 2 * x)


def polar(az_deg, el_deg, r):
    az, el = math.radians(az_deg), math.radians(el_deg)
    return np.array([r * math.sin(az) * math.cos(el), r * math.cos(az) * math.cos(el), r * math.sin(el)])


# ---- scene 2: voices burst from one point and circle the seat (7 s - 17.5 s)
VOICES = 8
VOICE_COL = [(0.25, 0.75, 1.0), (1.0, 0.55, 0.18), (0.55, 0.35, 1.0), (0.2, 1.0, 0.65),
             (1.0, 0.28, 0.5), (1.0, 0.85, 0.35), (0.35, 0.5, 1.0), (0.9, 0.95, 1.0)]


def voice_pos(i, t):
    u = t - 7.0
    out = smooth(0.0, 2.2, u)                    # leave the centre point
    back = smooth(8.6, 10.5, u)                  # drift up and forward into scene 3
    az = i * 360.0 / VOICES + 38.0 * u + 5.0 * u * u * (1 if i % 2 == 0 else 0.7)
    el = 6 + 16 * math.sin(0.9 * u + i * 1.7)
    r = 2.4 + 0.5 * math.sin(0.6 * u + i)
    p = polar(az, el, r)
    start = np.array([0.0, 3.0, 0.15])
    p = start * (1 - out) + p * out
    top = polar((i - 3.5) * 16, 52, 2.8)
    return p * (1 - back) + top * back


# ---- scene 3: drops from above (18.5 s - 27.6 s)
def _drops():
    rng = np.random.default_rng(11)
    out, t = [], 19.0
    while t < 27.4:
        az = rng.uniform(-75, 75) if rng.random() < 0.8 else rng.choice([-1, 1]) * rng.uniform(100, 140)
        r = rng.uniform(1.6, 4.2)
        out.append((t, float(az), float(r), int(rng.integers(0, 10))))
        t += float(rng.uniform(0.12, 0.34)) * (1.5 - smooth(19, 24, t))
    return out


DROPS = _drops()
FALL = 1.1                                       # seconds from ceiling to floor


def drop_pos(d, t):
    t0, az, r, _ = d
    k = np.clip((t - t0) / FALL, 0, 1)
    a = math.radians(az)
    return np.array([r * math.sin(a), r * math.cos(a), 2.6 - 3.5 * k * k])


# ---- scene 6: the fly-over (43.0 s - 45.0 s), screen -> ceiling -> behind
def flyover_pos(t):
    k = np.clip((t - 43.0) / 2.0, 0, 1)
    keys = np.array([[0.0, 6.0, 0.2], [-0.3, 3.4, 1.0], [0.1, 1.5, 2.4], [0.9, -0.4, 1.7], [1.6, -2.2, 0.3]])
    x = k ** 1.25 * (len(keys) - 1)
    i = min(int(x), len(keys) - 2)
    f = x - i
    p0, p1, p2, p3 = keys[max(i - 1, 0)], keys[i], keys[i + 1], keys[min(i + 2, len(keys) - 1)]
    return 0.5 * (2 * p1 + (p2 - p0) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (3 * p1 - p0 - 3 * p2 + p3) * f ** 3)


HIT = 45.0
PULSES = [HIT + 0.75 + k * (2.0 / 3.0) for k in range(9)]       # the 808s

# (in, out, on-screen caption or None, spoken line, voice loudness in LUFS). The voice starts 0.1 s after "in".
CAPTIONS = [
    (1.0, 3.8, "Every film arrives as a file.", "Every film arrives as a file.", -26.0),
    (4.2, 6.9, "Folded inside it is a room.", "Folded inside it, is a room.", -26.0),
    (9.6, 13.4, "Every sound has a place.", "Every sound has a place.", -24.0),
    (20.4, 25.4, "Some of those places are above you.", "Some of those places are above you.", -25.0),
    (28.6, 31.3, "Colour has its places too.", "Colour has its places too.", -25.0),
    (31.6, 34.8, "Inside this triangle: Rec.709.", "Inside this triangle: Rec seven oh nine.", -25.0),
    (35.8, 39.2, "And light is mapped to fit this screen.", "And light is mapped to fit this screen.", -25.0),
    (40.25, 42.15, "Leave the remote where it is.", "Leave the remote where it is.", -30.0),
    (54.2, 57.0, None, "Software defined home theatre.", -24.0),
]

# What each stretch is showing: (in, out, heading, description)
LABELS = [
    (0.5, 7.0, "SHADOW DETAIL", "near-black steps, in nits"),
    (7.4, 15.8, "OBJECT PANNING", "eight sounds moving around the seat"),
    (16.0, 19.8, "ASPECT RATIO", "scope opening to the full 16:9 frame"),
    (20.1, 27.6, "HEIGHT CHANNELS", "sound from the two ceiling speakers"),
    (28.2, 34.9, "COLOUR GAMUT", "Rec.709 on the CIE 1931 chromaticity chart"),
    (35.1, 39.8, "HDR10 TONE MAPPING", "patches up to 1000 nits, fitted to the screen by the player"),
    (40.1, 43.0, "DYNAMIC RANGE", "the quiet before the peak"),
    (43.0, 45.0, "OBJECT PANNING", "front to back, overhead"),
    (45.3, 51.4, "DYNAMICS AND LFE", "the loud end, with low-frequency effects"),
]
OPEN = (16.0, 19.2)                              # the frame grows from scope to 16:9
GAMUT_T = (28.6, 29.4, 30.2, 31.8)               # red, green, blue, white
HDR_NITS = [60, 100, 200, 400, 1000]
HDR_T = [35.3, 36.0, 36.7, 37.4, 38.1]
