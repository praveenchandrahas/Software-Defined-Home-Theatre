"""The rough mix: every sound of film II from the timeline, panned with Spatial-Lab's VBAP engine, on one bus per
scene so each scene's loudness can be set; then one gain for the whole film (true peak -3 dBTP, no limiter).

usage: python3 mix.py OUT.wav        (8 channels, 24-bit, 48 kHz, 7.1 file order)
"""
import sys
import numpy as np
from scipy import signal
from dsp import (T, FS, N, IDX, LFE, bus, tt, env, expdecay, filt, noise, pink, place, direct, doppler, bell, saw,
                 thump, pad, room, short_term_max, true_peak_db, to_file_order, write24, rng)


def spk(name, r=2.4):
    return np.array(T.SPEAKERS[name]) * r


def lfe(b, x, t0, gain):
    direct(b, filt(x, "low", 110, 4), t0, ["LFE"], gain)


# ------------------------------------------------------------------ 0-8 s: black
def s_open():
    b = bus()
    a0, a1 = T.AIR
    air = filt(pink(a1 - a0), "bandpass", [300, 3000], 2) * env(int((a1 - a0) * FS), 1.5, 1.2)
    place(b, air, a0, lambda t: T.polar(-60 + 50 * (t - a0), 25, 2.4), 1.0, spread=30)
    return b


# ------------------------------------------------------------------ 8-18 s: echoes
def ping_sound():
    t = tt(1.4)
    x = np.sin(2 * np.pi * 1320 * t) * np.exp(-t * 5) + 0.4 * np.sin(2 * np.pi * 1320 * 2.76 * t) * np.exp(-t * 9)
    x += 0.25 * np.sin(2 * np.pi * 330 * t) * np.exp(-t * 3)
    return x * env(len(t), 0.002, 0.2)


def s_echo():
    b = bus()
    send = np.zeros(N)
    w, d, h, f = T.ROOM["width"], T.ROOM["depth"], T.ROOM["height"], T.ROOM["front"]
    sx, sy, sz = T.ROOM["seat"]
    walls = [("x", -w / 2), ("x", w / 2), ("y", f - d), ("y", f), ("z", 0.0), ("z", h)]
    for tp, name in T.PINGS:
        src = np.array(sx, float) + 0, None
        dirv = np.array(T.SPEAKERS[name])
        x = ping_sound()
        direct(b, x, tp, [name], 0.8)
        i0 = int(tp * FS)
        send[i0:i0 + len(x)] += x * 0.5
        # an echo from each wall, when the drawn wave reaches it, from that wall's direction
        s = np.array([sx, sy, sz]) + dirv * 1.8
        for axis, pos in walls:
            k = "xyz".index(axis)
            dist = abs(pos - s[k])
            hit = s.copy(); hit[k] = pos
            rel = hit - np.array([sx, sy, sz])
            delay = dist / T.WAVE_SPEED
            e = filt(x, "low", 3500, 2) * 0.32
            place(b, e, tp + delay, lambda t, rel=rel: rel, 1.0, dist_gain=False)
    room(b, send, 2.6, 0.22)
    return b


# ------------------------------------------------------------------ 18-36 s: rain, building to a downpour under the storm
def s_rain():
    b = bus()
    r0, r1 = T.RAIN
    dur = r1 - r0
    t = tt(dur)
    dens = np.clip((t / 9.0) ** 2, 0, 1) * (1 - np.clip((t - (dur - 3)) / 3, 0, 1))       # peaks 27-33 s
    # the hiss of a lot of rain: its own noise in every speaker, heights strongest
    for nm, g in [("TFL", 1.0), ("TFR", 1.0), ("FL", 0.6), ("FR", 0.6), ("SL", 0.7), ("SR", 0.7), ("C", 0.3)]:
        x = filt(pink(dur), "bandpass", [1500, 12000], 2) * dens
        direct(b, x, r0, [nm], 0.09 * g)
    # single drops, placed mostly above: a short falling tone and a click
    count = 0
    for tk in np.arange(r0 + 0.2, r1, 0.01):
        p = np.interp(tk - r0, t[::480], dens[::480])
        if rng.random() > 0.02 + 0.9 * p * 0.5:
            continue
        f = rng.uniform(1400, 5200)
        n = int(0.05 * FS)
        tn = np.arange(n) / FS
        drop = np.sin(2 * np.pi * np.cumsum(f * (1 - 0.5 * tn / 0.05)) / FS) * np.exp(-tn * 90)
        drop[:24] += rng.standard_normal(24) * 0.5
        pos = T.polar(rng.uniform(-150, 150), rng.uniform(25, 85), 2.4)
        place(b, drop, tk, lambda _t, pos=pos: pos, rng.uniform(0.05, 0.16))
        count += 1
    return b


# ------------------------------------------------------------------ 30-42 s: storm
def thunder(b, t0, az, el):
    crack = filt(noise(0.35), "high", 900, 2) * expdecay(int(0.35 * FS), 0.05)
    crack += 0.6 * filt(noise(0.35), "bandpass", [200, 1600], 2) * expdecay(int(0.35 * FS), 0.12)
    place(b, crack, t0 + 0.02, lambda t: T.polar(az, el, 3.0), 1.2)
    # the roll: rumbling noise that travels from the strike over the ceiling towards the back
    d = 5.5
    n = int(d * FS)
    am = filt(np.abs(noise(d)), "low", 6, 2)
    am = am / am.max()
    roll = filt(noise(d), "low", 380, 3) * am * env(n, 0.15, 2.5) * expdecay(n, 2.2) * 2.2
    target = 180 if az >= 0 else -180

    def path(t):
        k = min(1.0, (t - t0) / d)
        return T.polar(az + (target - az) * k * 0.8, el + (75 - el) * np.sin(np.pi * min(k, 1.0)) * 0.6, 3.0)

    place(b, roll, t0 + 0.12, path, 1.0, spread=40)
    lfe(b, filt(noise(d), "bandpass", [46, 58], 2) * am * expdecay(n, 1.6) * 4.0, t0 + 0.1, 1.0)


def s_storm():
    b = bus()
    for t0, az, el in T.STRIKES:
        thunder(b, t0, az, el)
    # wind under it all
    d = T.CUT_TO_BLACK - 29.0
    for nm in ["FL", "FR", "SL", "SR", "TFL", "TFR"]:
        x = filt(pink(d), "bandpass", [120, 900], 2) * filt(np.abs(noise(d)), "low", 0.4, 1) * 3
        direct(b, x * env(len(x), 3.0, 0.01), 29.0, [nm], 0.25)
    return b


# ------------------------------------------------------------------ 42-50 s: one drop
def s_drop():
    b = bus()
    h = T.DROP_HIT
    t = tt(1.2)
    f = 900 + 900 * (1 - np.exp(-t * 40))
    plink = np.sin(2 * np.pi * np.cumsum(f) / FS) * np.exp(-t * 9) * env(len(t), 0.001, 0.2)
    direct(b, plink, h, ["C"], 0.5)
    body = thump(90, 50, 2.4, 6, 1.4)
    direct(b, body, h, ["C"], 0.5)
    lfe(b, body, h, 1.0)
    send = np.zeros(N)
    i0 = int(h * FS)
    send[i0:i0 + len(plink)] += plink
    room(b, send, 5.5, 0.25, predelay=40, damp=4000)
    # small ripples ticking outward, a little later
    for k in range(6):
        ripple = bell(2600 + 400 * k, 0.4, 14)
        place(b, ripple, h + 0.35 + 0.28 * k, lambda _t, k=k: T.polar(-70 + 28 * k, 5, 2.4), 0.05)
    return b


# ------------------------------------------------------------------ 50-65 s: canyon
def shepard(d, f_lo=40.0, octaves=7, rate=0.11):
    """Endless rise: octave-spaced tones gliding up, faded in at the bottom and out at the top."""
    t = tt(d)
    x = np.zeros(len(t))
    for k in range(octaves):
        pos = (k + rate * t) % octaves
        f = f_lo * 2 ** pos
        amp = np.exp(-0.5 * ((pos - octaves / 2) / (octaves / 5)) ** 2)
        x += amp * np.sin(2 * np.pi * np.cumsum(f) / FS)
    return x / octaves


def s_canyon():
    b = bus()
    t0, t1 = T.CANYON_ENTRY, T.SCENES["canyon"][1]
    d = t1 - t0
    # entry: a hit and a rush of air
    lfe(b, thump(80, 50, 1.6, 5, 1.8), t0, 1.0)
    direct(b, thump(120, 60, 0.8, 8, 4), t0, ["C"], 0.4)
    for nm in ["FL", "FR", "SL", "SR", "TFL", "TFR"]:
        wind = filt(pink(d), "bandpass", [180, 4500], 2) * env(int(d * FS), 0.05, 0.6)
        wind *= 0.6 + 0.4 * filt(np.abs(noise(d)), "low", 1.5, 1) / 0.8
        direct(b, wind, t0, [nm], 0.14)
    rise = shepard(T.OPEN[0] - t0 + 0.4) * env(int((T.OPEN[0] - t0 + 0.4) * FS), 2.0, 0.6)
    for nm in ["FL", "FR", "C", "SL", "SR"]:
        direct(b, rise, t0, [nm], 0.22)
    # the passes: a whoosh and a hum, with Doppler
    for i, (tp, side) in enumerate(T.PASSES):
        a = tp - 1.6
        n = int(2.6 * FS)
        hum = (saw(110 * (1 + 0.25 * (i % 4)), tt(2.6)) * 0.4 + filt(noise(2.6), "bandpass", [500, 6000], 2))
        y, r = doppler(hum, a, lambda t: T.pass_pos(t, tp, side))
        y = y / (1 + (r / 6) ** 1.4)
        y = filt(y, "low", 9000, 2) * env(n, 0.3, 0.4)
        place(b, y, a, lambda t: T.pass_pos(t, tp, side), 1.3, dist_gain=False)
    # the exit: everything rises, then lets go
    o0, o1 = T.OPEN
    sw = o1 - o0 + 1.0
    for nm in ["FL", "FR", "SL", "SR", "TFL", "TFR", "C"]:
        x = filt(pink(sw), "bandpass", [300, 9000], 2) * np.linspace(0, 1, int(sw * FS)) ** 2
        direct(b, x * env(len(x), 0.01, 0.6), o0, [nm], 0.16)
    pad(b, o0, sw + 0.4, [146.83, 220.0, 293.66, 369.99], ["FL", "FR", "SL", "SR", "TFL", "TFR"], 0.22, 1.2, 0.8, 4000, 0.5)
    lfe(b, np.sin(2 * np.pi * np.cumsum(47 + 9 * tt(sw) / sw) / FS) * np.linspace(0, 1, int(sw * FS)) ** 2, o0, 0.8)
    b[int((t1 + 0.15) * FS):] = 0
    fade = np.ones(N); i = int((t1 - 0.5) * FS); j = int((t1 + 0.15) * FS)
    fade[i:j] = np.linspace(1, 0, j - i); fade[j:] = 0
    return b * fade[:, None]


# ------------------------------------------------------------------ 65-75 s: orbit
def s_orbit():
    b = bus()
    t0, t1 = T.SCENES["earth"][0], T.FADE_OUT[1]
    pad(b, t0, t1 - t0, [73.42, 110.0, 146.83, 220.0, 277.18], ["TFL", "TFR", "SL", "SR", "FL", "FR"], 0.3, 2.5, 1.0, 1800)
    for k, f in enumerate([1174.66, 1479.98, 1760.0, 2217.46]):
        x = bell(f, 4.5, 0.6)
        place(b, x, T.SUN_CREST + 0.12 * k, lambda _t, k=k: T.polar(-12 + 8 * k, 18, 2.4), 0.12)
    fade = np.ones(N); i, j = int(T.FADE_OUT[0] * FS), int(T.FADE_OUT[1] * FS)
    fade[i:j] = np.linspace(1, 0, j - i) ** 2; fade[j:] = 0
    return b * fade[:, None]


# ------------------------------------------------------------------ 78-90 s: pressure wave
def braam(d, f=55.0):
    t = tt(d)
    x = sum(saw(f * m * (1 + det), t) for m in (1, 2) for det in (-0.006, -0.002, 0.003, 0.007))
    x = np.tanh(1.8 * x / 4)
    out = np.zeros_like(x)
    blocks = int(np.ceil(len(x) / 4800))
    for k in range(blocks):
        a, c = k * 4800, min(len(x), (k + 1) * 4800)
        fc = 250 + 3200 * np.exp(-(a / FS) * 0.9)
        out[a:c] = filt(x[max(0, a - 4800):c], "low", fc, 2)[-(c - a):]
    return out * env(len(x), 0.03, 1.5) * expdecay(len(x), 2.6)


def s_hit():
    b = bus()
    h = T.HIT
    br = braam(6.0)
    for nm in ["FL", "FR", "C", "SL", "SR", "TFL", "TFR"]:
        direct(b, br * rng.uniform(0.9, 1.1), h + rng.uniform(0, 0.004), [nm], 0.22)
    imp = filt(noise(1.2), "low", 2500, 2) * expdecay(int(1.2 * FS), 0.12)
    for nm in ["FL", "FR", "C", "TFL", "TFR"]:
        direct(b, imp, h, [nm], 0.5)
    drop = np.sin(2 * np.pi * np.cumsum(48 + 30 * np.exp(-tt(2.5) * 1.6)) / FS) * env(int(2.5 * FS), 0.005, 0.6)
    lfe(b, drop, h, 1.0)
    # debris flying out past the listener
    for k in range(140):
        t0 = h + rng.uniform(0.02, 1.6)
        g = bell(rng.uniform(1800, 7000), 0.12, 30, ((1, 1.0), (2.7, 0.3)))
        az = rng.uniform(-40, 40)
        place(b, g, t0, lambda t, az=az, t0=t0: T.polar(az + (180 if az > 0 else -180) * min(1, (t - t0) * 3), rng.uniform(-5, 40), 2.4),
              rng.uniform(0.03, 0.09))
    send = np.zeros(N); i0 = int(h * FS); send[i0:i0 + len(imp)] += imp
    room(b, send, 4.0, 0.3, predelay=30, damp=3000)
    # thumps: an 808 in the sub and centre, a slap that walks round the room
    order = ["FL", "FR", "SR", "SL", "TFL", "TFR"]
    for k, t in enumerate(T.THUMPS):
        kick = thump(95, 50, 0.6, 9, 4.5)
        lfe(b, kick, t, 0.9)
        direct(b, kick, t, ["C"], 0.35)
        direct(b, filt(noise(0.08), "bandpass", [600, 4000], 2) * expdecay(int(0.08 * FS), 0.015), t, [order[k % 6]], 0.35)
    pad(b, T.THUMPS[0], 10.5, [55.0, 82.41, 110.0], ["FL", "FR", "SL", "SR"], 0.25, 2.0, 2.0, 900)
    return b


# ------------------------------------------------------------------ 90-100 s: title
def s_title():
    b = bus()
    t0 = T.TITLE_IN[0] - 1.0
    d = T.LIGHT_OUT - t0
    pad(b, t0, d, [110.0, 164.81, 220.0, 277.18, 329.63, 440.0], ["FL", "FR", "C", "SL", "SR", "TFL", "TFR"], 0.2, 2.5, 0.02, 3200, 0.4)
    lfe(b, np.sin(2 * np.pi * 55 * tt(d)) * env(int(d * FS), 3.0, 0.02), t0, 0.25)
    b[int(T.LIGHT_OUT * FS):] = 0                           # lights out: the sound goes with them
    return b


def s_ticks():
    """The first and last sound: one small tick in each ceiling speaker, at a fixed level (peak -24 dBFS)."""
    b = bus()
    n = int(0.12 * FS)
    for t0, name, f in [(T.TICK_L, "TFL", 920), (T.TICK_R, "TFR", 980)]:
        tick = filt(noise(0.12), "bandpass", [1800, 5200], 2) * expdecay(n, 0.006) + 0.6 * np.sin(2 * np.pi * f * tt(0.12)) * expdecay(n, 0.03)
        direct(b, tick / np.max(np.abs(tick)) * 10 ** (-24 / 20), t0, [name])
    return b


# The room, from the rattle sweep (2026-11-28): a cabinet in the room buzzes at 60-67 Hz even at -21 dBFS in the LFE;
# the sub's cabinet buzzes at 30-38 Hz from -15 dBFS and up to 45 Hz from -9 dBFS. Clean at every level tried:
# 47-57 Hz and 71-99 Hz. So the low end is built there: a notch at 63.6 Hz on everything, and the LFE high-passed at 45 Hz.
RATTLE_HZ = 63.6
SUB_FLOOR_HZ = 45.0


def protect(x):
    b, a = signal.iirnotch(RATTLE_HZ, 2.5, FS)
    y = signal.filtfilt(b, a, x, axis=0)
    return y


# (function, window to measure, target short-term LUFS, LFE peak dBFS or None)
PLAN = [(s_open, (2.5, 8.5), -44.0, None), (s_echo, (8.0, 18.0), -29.0, None), (s_rain, (18.0, 36.0), -25.0, None),
        (s_storm, (30.0, 42.0), -19.0, -9.0), (s_drop, (45.5, 50.0), -27.0, -10.0), (s_canyon, (50.0, 65.0), -18.0, -8.0),
        (s_orbit, (65.0, 75.0), -30.0, None), (s_hit, (77.8, 90.0), -12.0, -6.0), (s_title, (90.0, 98.0), -25.0, -20.0),
        (s_ticks, None, None, None)]


def build():
    mix = np.zeros((N, 8))
    report = []
    for fn, win, target, lfe_peak in PLAN:
        a, c = win or (0, 0)
        b = fn()
        l = b[:, LFE].copy(); b[:, LFE] = 0
        g = 1.0 if target is None else 10 ** ((target - short_term_max(b, a, c)) / 20)
        b *= g
        if lfe_peak is not None and np.max(np.abs(l)) > 0:
            b[:, LFE] = filt(l, "high", 28, 4) * (10 ** (lfe_peak / 20) / np.max(np.abs(l)))
        mix += b
        report.append((fn.__name__, target, round(20 * np.log10(g), 1)))
    mix = protect(mix)
    mix[:, LFE] = filt(mix[:, LFE], "high", SUB_FLOOR_HZ, 4)
    mix[:, LFE] *= 10 ** (-6 / 20) / np.max(np.abs(mix[:, LFE]))      # the filters took some level: back to -6 dBFS peak
    # digital zero where the film says so
    for a, c in [(0.0, T.TICK_L - 0.01), (T.CUT_TO_BLACK, T.DROP_FALL[0]), T.SILENCE, (T.LIGHT_OUT, T.TICK_R - 0.01),
                 (T.TICK_R + 0.2, T.DUR)]:
        mix[int(a * FS):int(c * FS)] = 0
    tp = true_peak_db(mix)
    if tp > -3.0:
        mix *= 10 ** ((-3.0 - tp) / 20)
    return mix, report


if __name__ == "__main__":
    out = sys.argv[1]
    mix, report = build()
    for r in report:
        print("%-9s target %6s LUFS  gain %+6.1f dB" % (r[0], "fixed" if r[1] is None else "%.1f" % r[1], r[2]))
    for name, (a, c) in [("open", (2.5, 8.5)), ("echo", (8, 18)), ("rain", (18, 30)), ("storm", (30, 42)), ("drop", (45.5, 50)),
                         ("canyon", (50, 65)), ("orbit", (65, 75)), ("hit", (77.8, 90)), ("title", (90, 98))]:
        print("%-7s short-term max %6.1f LUFS" % (name, short_term_max(mix, a, c)))
    print("true peak %.2f dBTP, LFE peak %.1f dBFS" % (true_peak_db(mix), 20 * np.log10(np.max(np.abs(mix[:, LFE])) + 1e-12)))
    write24(out, to_file_order(mix))
    print("wrote", out)
