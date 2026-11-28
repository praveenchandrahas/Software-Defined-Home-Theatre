"""Synthesise every sound and pan it to 5.1.2 along the score's paths. Writes a 7.1-ordered 24-bit WAV."""
import sys, wave
import numpy as np
from scipy import signal
from scipy.io import wavfile
import score as S
from vbap import Vbap

FS = S.FS
N = int(S.DUR * FS)
NAMES = S.VBAP_ORDER + ["LFE"]
IDX = {n: i for i, n in enumerate(NAMES)}
vb = Vbap(np.array([S.SPEAKERS[n] for n in S.VBAP_ORDER]))
rng = np.random.default_rng(5)


def tt(d):
    return np.arange(int(d * FS)) / FS


def env(n, a, r):
    e = np.ones(n)
    na, nr = min(int(a * FS), n), min(int(r * FS), n)
    e[:na] *= np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    e[n - nr:] *= np.sin(np.linspace(np.pi / 2, 0, nr)) ** 2
    return e


def filt(x, kind, f, order=4):
    return signal.sosfilt(signal.butter(order, f, kind, fs=FS, output="sos"), x)


def noise(d):
    return rng.standard_normal(int(d * FS))


def place(bus, mono, t0, posfn, gain=1.0, spread=0.0, block=512):
    """Pan a mono sound along posfn(time). Gains ramp across each block."""
    i0 = int(t0 * FS)
    n = min(len(mono), N - i0)
    edges = list(range(0, n, block)) + [n]

    def g_at(k):
        p = posfn(t0 + k / FS)
        r = max(np.linalg.norm(p), 0.5)
        return vb.gains_spread(p, spread) * min(1.35, (2.4 / r) ** 0.6)

    prev = g_at(0)
    for a, b in zip(edges[:-1], edges[1:]):
        cur = g_at(b)
        ramp = np.linspace(0, 1, b - a, endpoint=False)[:, None]
        bus[i0 + a:i0 + b, :7] += gain * mono[a:b, None] * (prev * (1 - ramp) + cur * ramp)
        prev = cur


def direct(bus, mono, t0, names, gain=1.0):
    i0 = int(t0 * FS)
    n = min(len(mono), N - i0)
    for nm in names:
        bus[i0:i0 + n, IDX[nm]] += gain * mono[:n]


def static(p):
    p = np.array(p, float)
    return lambda t: p


def bell(f, d, decay=1.6):
    t = tt(d)
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * decay * (1 + 0.9 * k))
            for k, (m, a) in enumerate([(1, 1.0), (2.01, 0.35), (3.02, 0.16), (4.17, 0.08)]))
    return x * env(len(t), 0.008, 0.2)


def pad(bus, t0, d, freqs, names, gain, a=2.0, r=2.0, lp=2500):
    """A wide pad: each speaker gets its own detune and phase, so the channels are decorrelated."""
    t = tt(d)
    for nm in names:
        x = 0
        for f in freqs:
            for det in (-1, 1):
                fd = f * (1 + det * rng.uniform(0.001, 0.004))
                x = x + np.sin(2 * np.pi * fd * t + rng.uniform(0, 6.28)) + 0.25 * np.sin(4 * np.pi * fd * t + rng.uniform(0, 6.28))
        x = filt(x / (2 * len(freqs)), "low", lp, 2) * env(len(t), a, r)
        direct(bus, x, t0, [nm], gain)


# ---------------------------------------------------------------- scenes, each on its own bus so its loudness can be set
def scene_open():
    b = np.zeros((N, 8))
    for t0, f, g in [(0.6, 523.25, .8), (2.1, 783.99, .5), (3.4, 659.25, .6), (4.7, 1046.5, .35), (5.6, 587.33, .4)]:
        direct(b, bell(f, 2.6), t0, ["C"], g)
    air = filt(noise(7.0), "bandpass", [600, 3000], 2) * env(int(7 * FS), 3.0, 1.0)
    direct(b, air, 0.0, ["C"], 0.012)
    return b


def scene_orbit():
    b = np.zeros((N, 8))
    notes = [261.63, 329.63, 392.0, 493.88, 587.33, 739.99, 880.0, 1174.66]
    d = 10.8
    t = tt(d)
    for i in range(S.VOICES):
        f = notes[i]
        rate = 1.5 + 0.35 * i
        gate = np.exp(-6 * ((t * rate + i * 0.37) % 1.0))
        x = (np.sin(2 * np.pi * f * t + 1.8 * gate * np.sin(2 * np.pi * f * 2 * t)) * gate
             + 0.28 * np.sin(2 * np.pi * f * t))
        x *= env(len(t), 0.8, 1.2) * (330.0 / max(f, 330.0)) ** 0.4
        place(b, x, 7.0, lambda tm, i=i: S.voice_pos(i, tm), 0.5)
    pad(b, 7.0, 11.0, [65.41, 98.0, 130.81], ["FL", "FR", "SL", "SR"], 0.28, 2.5, 2.5, 900)
    whoosh = filt(noise(2.4), "bandpass", [250, 2500], 2) * np.sin(np.linspace(0, np.pi, int(2.4 * FS))) ** 3
    place(b, whoosh, 6.6, static([0, 3, 0.2]), 0.35, spread=40)
    return b


def scene_rain():
    b = np.zeros((N, 8))
    # a rise from the screen to the ceiling
    d = 3.0
    t = tt(d)
    f = 220 * 2 ** (2.2 * (t / d) ** 1.5)
    rise = (np.sin(2 * np.pi * np.cumsum(f) / FS) + 0.5 * filt(noise(d), "high", 1500, 2) * (t / d)) * env(len(t), 1.5, 0.5)
    place(b, rise, 16.8, lambda tm: np.array([0.0, 3.0 - 1.8 * S.smooth(16.8, 19.8, tm), 0.1 + 2.5 * S.smooth(16.8, 19.8, tm)]), 0.28, spread=15)
    scale = [1046.5, 1174.66, 1318.5, 1568.0, 1760.0, 2093.0, 2349.3, 2637.0, 3136.0, 3520.0]
    for dr in S.DROPS:
        t0, _, _, note = dr
        x = bell(scale[note], 1.1, 5.0)
        tick = filt(noise(0.012), "high", 3000, 2) * np.linspace(1, 0, int(0.012 * FS)) ** 2
        x[:len(tick)] += 0.7 * tick
        place(b, x, t0, lambda tm, dr=dr: S.drop_pos(dr, tm), 0.34)
    for nm in ["TFL", "TFR"]:
        sh = filt(noise(10.5), "bandpass", [1200, 7000], 2) * env(int(10.5 * FS), 3.0, 2.5)
        direct(b, sh, 17.8, [nm], 0.035)
    pad(b, 17.5, 11.0, [220.0, 329.63, 493.88], ["TFL", "TFR"], 0.13, 3.0, 3.0, 3000)
    pad(b, 17.5, 11.0, [73.42, 110.0], ["FL", "FR", "SL", "SR"], 0.17, 3.0, 3.0, 700)
    return b


def scene_frame():
    """The swell under the opening frame: air spreading to every speaker and a low rise in the sub."""
    b = np.zeros((N, 8))
    t0, t1 = S.OPEN
    d = t1 - t0 + 1.2
    t = tt(d)
    shape = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    for nm in ["FL", "FR", "SL", "SR", "TFL", "TFR"]:
        direct(b, filt(noise(d), "bandpass", [120, 1800], 2) * shape * (t / d), t0 - 0.3, [nm], 0.1)
    pad(b, t0 - 0.3, d, [87.31, 130.81, 174.61, 261.63], ["FL", "FR", "SL", "SR", "TFL", "TFR"], 0.2, 2.0, 1.6, 1800)
    f = 34 + 24 * S.smooth(0.0, d, t)
    direct(b, np.sin(2 * np.pi * np.cumsum(f) / FS) * shape, t0 - 0.3, ["LFE"], 1.0)
    return b


def scene_gamut():
    b = np.zeros((N, 8))
    for t0, f, names in zip(S.GAMUT_T, [392.0, 493.88, 587.33], [["FL"], ["TFL", "TFR"], ["FR"]]):
        direct(b, bell(f, 3.2, 1.2), t0, names, 0.45 if len(names) == 1 else 0.3)
    for f in [783.99, 987.77, 1174.66]:                  # all three together: white
        direct(b, bell(f, 3.0, 1.2), S.GAMUT_T[3], ["C", "FL", "FR"], 0.14)
    pad(b, 28.0, 7.2, [98.0, 146.83, 196.0], ["FL", "FR", "SL", "SR"], 0.2, 1.5, 1.5, 900)
    return b


def scene_hdr():
    """One tone per patch, each higher and louder than the last."""
    b = np.zeros((N, 8))
    for k, (t0, f) in enumerate(zip(S.HDR_T, [293.66, 369.99, 440.0, 587.33, 880.0])):
        direct(b, bell(f, 1.8, 2.2), t0, [["FL"], ["C"], ["FR"], ["SR"], ["TFL", "TFR"]][k][0:2], 0.18 + 0.1 * k)
    pad(b, 35.0, 5.0, [73.42, 110.0, 220.0], ["FL", "FR", "SL", "SR"], 0.16, 1.0, 1.0, 1200)
    return b


def thump(f_hi, f_lo, d, sweep_rate, decay):
    t = tt(d)
    f = f_lo + (f_hi - f_lo) * np.exp(-t * sweep_rate)
    return np.sin(2 * np.pi * np.cumsum(f) / FS) * np.exp(-t * decay) * env(len(t), 0.004, 0.25)


def scene_hit():
    """Returns (sound for the satellites and heights, LFE) in one bus; the LFE is level-set separately."""
    b = np.zeros((N, 8))
    d = 2.1
    t = tt(d)
    rush = filt(noise(d), "bandpass", [180, 4000], 2) * (t / d) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(300 - 160 * (t / d)) / FS) * (t / d) ** 2
    place(b, (rush + 0.6 * tone) * env(len(t), 0.05, 0.12), 43.0, S.flyover_pos, 0.55)
    # the hit
    body = thump(190, 55, 2.6, 14, 1.9)
    direct(b, body, S.HIT, ["FL", "FR", "C"], 0.50)
    for nm in ["FL", "FR", "SL", "SR", "TFL", "TFR"]:
        crack = filt(noise(2.4), "bandpass", [160, 6000], 2) * np.exp(-tt(2.4) * 3.0)
        direct(b, crack * env(len(crack), 0.002, 0.3), S.HIT, [nm], 0.12)
    direct(b, thump(95, 38, 3.2, 3.5, 1.3), S.HIT, ["LFE"], 1.0)
    for i, tp in enumerate(S.PULSES):
        direct(b, thump(120, 47 if i % 4 != 3 else 41, 0.62, 28, 4.2), tp, ["LFE"], 0.72)
        click = thump(900, 160, 0.09, 90, 40)
        direct(b, click, tp, ["FL", "FR"], 0.20)
        hat = filt(noise(0.07), "high", 6000, 2) * np.exp(-tt(0.07) * 60)
        direct(b, hat, tp + 1.0 / 3.0, ["SL" if i % 2 else "SR"], 0.10)
    pad(b, S.HIT, 8.0, [73.42, 110.0, 146.83, 220.0, 369.99], ["FL", "FR", "SL", "SR", "TFL", "TFR"], 0.17, 0.05, 3.0, 2200)
    return b


def scene_title():
    b = np.zeros((N, 8))
    pad(b, 51.6, 7.4, [146.83, 220.0, 293.66, 440.0], ["FL", "FR", "SL", "SR", "TFL", "TFR"], 0.18, 1.2, 4.0, 2400)
    for t0, f in [(52.6, 587.33), (53.1, 880.0), (53.6, 1174.66)]:
        direct(b, bell(f, 3.4, 1.2), t0, ["C"], 0.45)
    direct(b, bell(1046.5, 2.2, 2.0), 57.4, ["C"], 0.25)
    return b


# ---------------------------------------------------------------- loudness (BS.1770 K-weighting), heights weighted 1.0
KB1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]; KA1 = [1.0, -1.69065929318241, 0.73248077421585]
KB2 = [1.0, -2.0, 1.0]; KA2 = [1.0, -1.99004745483398, 0.99007225036621]
WEIGHT = np.array([1, 1, 1, 1, 1, 1.41, 1.41, 0.0])


def short_term_max(x, t0, t1):
    seg = x[int(t0 * FS):int(t1 * FS)]
    k = signal.lfilter(KB2, KA2, signal.lfilter(KB1, KA1, seg, axis=0), axis=0)
    p = (k ** 2) @ WEIGHT
    w = min(int(3 * FS), len(p))
    c = np.concatenate([[0], np.cumsum(p)])
    return -0.691 + 10 * np.log10(np.max((c[w:] - c[:-w]) / w) + 1e-20)


def true_peak_db(x):
    return 20 * np.log10(max(np.max(np.abs(signal.resample_poly(x[:, i], 4, 1))) for i in range(x.shape[1])) + 1e-20)


def to_file_order(x):
    return x[:, [IDX[n] for n in S.FILE_ORDER]]


def write24(path, x):
    d = np.clip(np.round(x * 8388607), -8388608, 8388607).astype("<i4")
    raw = d.reshape(-1, 1).view(np.uint8)[:, :3].tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(3); w.setframerate(FS); w.writeframes(raw)


def line_loudness(x):
    k = signal.lfilter(KB2, KA2, signal.lfilter(KB1, KA1, x))
    return -0.691 + 10 * np.log10(np.mean(k ** 2) + 1e-20)


def voice_track(folder):
    """The generated lines (voice.py) on the centre speaker, and the gain that ducks everything else under them."""
    v = np.zeros(N)
    duck = np.ones(N)
    now = np.arange(N) / FS
    for i, (t0, t1, _, _, lufs) in enumerate(S.CAPTIONS):
        sr, x = wavfile.read("%s/%02d.wav" % (folder, i))
        x = x.astype(float) / (np.iinfo(x.dtype).max if x.dtype.kind == "i" else 1)
        x = filt(signal.resample_poly(x, FS, sr), "high", 70, 2)
        x *= 10 ** ((lufs - line_loudness(x)) / 20) * env(len(x), 0.01, 0.05)
        i0 = int((t0 + 0.1) * FS)
        assert len(x) / FS <= t1 - t0, "voice line %d is longer than its caption" % i
        v[i0:i0 + len(x)] += x
        end = t0 + 0.1 + len(x) / FS
        duck = np.minimum(duck, 1 - 0.5 * (S.smooth(t0 - 0.2, t0 + 0.15, now) - S.smooth(end, end + 0.45, now)))
    return v, duck


def build(voice="vo"):
    # (scene, window used to measure it, target short-term loudness in LUFS, LFE peak in dBFS or None)
    plan = [(scene_open, (0, 7), -33.0, None), (scene_orbit, (8, 16), -23.0, None), (scene_frame, (16, 19.6), -23.0, -17.0),
            (scene_rain, (19, 27), -27.0, None), (scene_gamut, (28, 35), -28.0, None), (scene_hdr, (35, 39.2), -27.0, None),
            (scene_hit, (44.5, 50), -14.0, -9.0), (scene_title, (52, 58), -24.0, None)]
    mix = np.zeros((N, 8))
    report = []
    for fn, (a, b), target, lfe_peak in plan:
        bus = fn()
        lfe = bus[:, 7].copy(); bus[:, 7] = 0
        g = 10 ** ((target - short_term_max(bus, a, b)) / 20)
        bus *= g
        if lfe_peak is not None:                     # LFE set by peak: it does not count towards loudness
            bus[:, 7] = filt(lfe * (10 ** (lfe_peak / 20) / np.max(np.abs(lfe))), "high", 30, 4)
        mix += bus
        report.append((fn.__name__, target, round(20 * np.log10(g), 1)))
    # true silence before the fly-over: everything earlier fades by 40.0, the hit scene starts at 43.0
    fade = 1 - S.smooth(39.2, 40.0, np.arange(N) / FS)
    fade[int(43.0 * FS):] = 1
    mix *= fade[:, None]
    if voice:
        v, duck = voice_track(voice)
        mix *= duck[:, None]
        mix[:, IDX["C"]] += v
    mix[-int(0.4 * FS):] *= np.linspace(1, 0, int(0.4 * FS))[:, None]
    tp = true_peak_db(mix)
    if tp > -3.0:                                    # one gain for the whole film, no limiter
        mix *= 10 ** ((-3.0 - tp) / 20)
    return mix, report


if __name__ == "__main__":
    voice = sys.argv[2] if len(sys.argv) > 2 else "vo"      # "" for a track without the voice
    mix, report = build(voice)
    write24(sys.argv[1], to_file_order(mix))
    for r in report:
        print("scene %-14s target %5.1f LUFS, gain %+.1f dB" % r)
    print("true peak %.2f dBTP" % true_peak_db(mix))
    for name, a, b in [("open", 0, 7), ("orbit", 8, 16), ("rain", 19, 27), ("frame", 16, 19.6), ("gamut", 28, 35), ("hdr", 35, 39.2), ("hit", 44.5, 50), ("title", 52, 58)]:
        print("  %-8s short-term max %.1f LUFS" % (name, short_term_max(mix, a, b)))
    print("silence 42.2-42.95 s peak:", np.max(np.abs(mix[int(42.2 * FS):int(42.95 * FS)])))
    print("peak per channel (dBFS):", {n: round(float(20 * np.log10(np.max(np.abs(mix[:, i])) + 1e-12)), 1) for i, n in enumerate(NAMES)})
