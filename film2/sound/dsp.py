"""Signal helpers for the mix. Bus layout: 7 speaker channels in VBAP order, then LFE."""
import os, sys, wave
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "intro"))
import timeline as T          # noqa: E402
from vbap import Vbap         # noqa: E402  (Spatial-Lab's engine, copied into intro/)

FS = T.FS
N = int(T.DUR * FS)
NAMES = T.VBAP_ORDER + ["LFE"]
IDX = {n: i for i, n in enumerate(NAMES)}
LFE = IDX["LFE"]
vb = Vbap(np.array([T.SPEAKERS[n] for n in T.VBAP_ORDER]))
rng = np.random.default_rng(23)
C_SOUND = 343.0


def bus():
    return np.zeros((N, 8))


def tt(d):
    return np.arange(int(d * FS)) / FS


def env(n, a, r):
    e = np.ones(n)
    na, nr = min(int(a * FS), n), min(int(r * FS), n)
    if na:
        e[:na] *= np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if nr:
        e[n - nr:] *= np.sin(np.linspace(np.pi / 2, 0, nr)) ** 2
    return e


def expdecay(n, tau):
    return np.exp(-np.arange(n) / FS / tau)


def filt(x, kind, f, order=4):
    return signal.sosfilt(signal.butter(order, f, kind, fs=FS, output="sos"), x, axis=0)


def noise(d):
    return rng.standard_normal(int(d * FS))


def pink(d):
    x = noise(d)
    b, a = [0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, x) * 8


def place(b, mono, t0, posfn, gain=1.0, spread=0.0, block=256, dist_gain=True):
    """Pan a mono sound along posfn(film time) -> (x, y, z) metres from the seat."""
    i0 = int(round(t0 * FS))
    if i0 < 0:
        mono, i0 = mono[-i0:], 0
    n = min(len(mono), N - i0)
    if n <= 0:
        return
    edges = list(range(0, n, block)) + [n]

    def g_at(k):
        p = np.asarray(posfn(t0 + k / FS), float)
        r = max(np.linalg.norm(p), 0.3)
        g = vb.gains_spread(p, spread) if spread else vb.gains(p)
        return g * (min(1.6, (2.4 / r) ** 0.8) if dist_gain else 1.0)

    prev = g_at(0)
    for a, c in zip(edges[:-1], edges[1:]):
        cur = g_at(c)
        ramp = np.linspace(0, 1, c - a, endpoint=False)[:, None]
        b[i0 + a:i0 + c, :7] += gain * mono[a:c, None] * (prev * (1 - ramp) + cur * ramp)
        prev = cur


def direct(b, mono, t0, names, gain=1.0):
    i0 = int(round(t0 * FS))
    if i0 < 0:
        mono, i0 = mono[-i0:], 0
    n = min(len(mono), N - i0)
    for nm in names:
        b[i0:i0 + n, IDX[nm]] += gain * mono[:n]


def doppler(x, t0, posfn):
    """Delay x by the moving distance (variable delay line), so pitch shifts as the source passes."""
    n = len(x)
    t = t0 + np.arange(n) / FS
    P = np.array([posfn(tk) for tk in t[::64]])
    r = np.interp(np.arange(n), np.arange(0, n, 64)[:len(P)], np.linalg.norm(P, axis=1))
    src = np.arange(n) - (r - r.min()) / C_SOUND * FS
    y = np.interp(src, np.arange(n), x, left=0, right=0)
    return y, r


def bell(f, d, decay=1.6, partials=((1, 1.0), (2.01, 0.35), (3.02, 0.16), (4.17, 0.08))):
    t = tt(d)
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * decay * (1 + 0.9 * k)) for k, (m, a) in enumerate(partials))
    return x * env(len(t), 0.004, 0.2)


def saw(f, t):
    return 2 * ((f * t) % 1.0) - 1


def thump(f_hi, f_lo, d, sweep, decay):
    t = tt(d)
    f = f_lo + (f_hi - f_lo) * np.exp(-t * sweep)
    return np.sin(2 * np.pi * np.cumsum(f) / FS) * np.exp(-t * decay) * env(len(t), 0.002, 0.05)


def pad(b, t0, d, freqs, names, gain, a=2.0, r=2.0, lp=2500, bright=0.25):
    """Each speaker gets its own detune and phase, so the channels are decorrelated (enveloping, not a phantom point)."""
    t = tt(d)
    for nm in names:
        x = 0
        for f in freqs:
            for det in (-1, 1):
                fd = f * (1 + det * rng.uniform(0.001, 0.004))
                x = x + np.sin(2 * np.pi * fd * t + rng.uniform(0, 6.28)) + bright * np.sin(4 * np.pi * fd * t + rng.uniform(0, 6.28))
        x = filt(x / (2 * len(freqs)), "low", lp, 2) * env(len(t), a, r)
        direct(b, x, t0, [nm], gain)


_engine = None
_count = [0]


def reverb(mono, seconds=3.0, predelay_ms=20, damp_hz=6000, seed=0):
    """Faust zita_rev1 (stereo out) on a mono send; returns (N, 2)."""
    global _engine
    import dawdreamer as daw
    _engine = daw.RenderEngine(FS, 512)          # a fresh engine each call: processors are not reusable across graphs
    _count[0] += 1
    f = _engine.make_faust_processor("rev%d" % _count[0])
    f.set_dsp_string('import("stdfaust.lib"); process = re.zita_rev1_stereo(%d, 200, %d, %.2f, %.2f, %d);'
                     % (predelay_ms, damp_hz, seconds, seconds * 0.8, FS))
    x = np.stack([mono, np.roll(mono, 7 + seed)]).astype(np.float32)
    pb = _engine.make_playback_processor("in%d" % _count[0], x)
    _engine.load_graph([(pb, []), (f, ["in%d" % _count[0]])])
    _engine.render(len(mono) / FS)
    y = _engine.get_audio().T
    out = np.zeros((len(mono), 2))
    out[:min(len(y), len(mono))] = y[:len(mono)]
    return out


def room(b, send, seconds, gain, names=("FL", "FR", "SL", "SR", "TFL", "TFR"), predelay=25, damp=6000):
    """Spread a reverb of `send` over speaker pairs with different predelays (decorrelated tail)."""
    pairs = [(names[k], names[k + 1]) for k in range(0, len(names), 2)]
    for i, (l, r) in enumerate(pairs):
        y = reverb(send, seconds, predelay + 9 * i, damp, seed=i)
        b[:, IDX[l]] += gain * y[:, 0]
        b[:, IDX[r]] += gain * y[:, 1]


# ---------------------------------------------------------------- measuring
KB1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]; KA1 = [1.0, -1.69065929318241, 0.73248077421585]
KB2 = [1.0, -2.0, 1.0]; KA2 = [1.0, -1.99004745483398, 0.99007225036621]
WEIGHT = np.array([1, 1, 1, 1, 1, 1.41, 1.41, 0.0])   # BS.1770: side surrounds +1.5 dB; heights 1.0; LFE not counted


def k_weighted_power(x):
    k = signal.lfilter(KB2, KA2, signal.lfilter(KB1, KA1, x, axis=0), axis=0)
    return (k ** 2) @ WEIGHT


def short_term(x, step=0.1):
    """Short-term loudness (3 s windows) every `step` seconds; returns (times, LUFS)."""
    p = k_weighted_power(x)
    w = int(3 * FS)
    c = np.concatenate([[0], np.cumsum(p)])
    idx = np.arange(w, len(p) + 1, int(step * FS))
    return idx / FS, -0.691 + 10 * np.log10((c[idx] - c[idx - w]) / w + 1e-20)


def short_term_max(x, t0, t1):
    seg = x[int(t0 * FS):int(t1 * FS)]
    return short_term(seg)[1].max() if len(seg) > 3 * FS else -0.691 + 10 * np.log10(np.mean(k_weighted_power(seg)) + 1e-20)


def true_peak_db(x):
    return 20 * np.log10(max(np.max(np.abs(signal.resample_poly(x[:, i], 4, 1))) for i in range(x.shape[1])) + 1e-20)


def to_file_order(x):
    return x[:, [IDX[n] for n in T.FILE_ORDER]]


def write24(path, x):
    d = np.clip(np.round(x * 8388607), -8388608, 8388607).astype("<i4")
    raw = d.reshape(-1, 1).view(np.uint8)[:, :3].tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(3); w.setframerate(FS); w.writeframes(raw)
