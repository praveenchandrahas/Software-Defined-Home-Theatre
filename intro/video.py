"""Render the picture in linear light (nits) and write HDR10 and SDR streams.

usage: video.py OUT_HDR.mkv OUT_SDR.mkv [--labels] [--stills 3,12,24] [--range A B]
"""
import sys, subprocess, math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import score as S

W, H = 1920, 1080
SCOPE_H = 804
FOCAL = (W / 2) / math.tan(math.radians(96) / 2)
FONT = "/usr/share/fonts/opentype/inter/Inter-%s.otf"
cv2.setNumThreads(2)


# ------------------------------------------------------------------ camera and splatting
def project(p, pitch):
    c, s = math.cos(pitch), math.sin(pitch)
    y = p[:, 1] * c + p[:, 2] * s
    z = -p[:, 1] * s + p[:, 2] * c
    ok = y > 0.25
    yy = np.where(ok, y, 1.0)
    return W / 2 + FOCAL * p[:, 0] / yy, H / 2 - FOCAL * z / yy, y, ok


def splat(buf, x, y, rgb):
    """Add points (bilinear). rgb: (n, 3) nits."""
    x = x - 0.5; y = y - 0.5
    m = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
    if not m.any():
        return
    x, y, rgb = x[m], y[m], rgb[m]
    xi, yi = x.astype(np.int64), y.astype(np.int64)
    fx, fy = x - xi, y - yi
    base = yi * W + xi
    idx = np.concatenate([base, base + 1, base + W, base + W + 1])
    wt = np.concatenate([(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy])
    for c in range(3):
        buf[:, :, c] += np.bincount(idx, weights=wt * np.tile(rgb[:, c], 4), minlength=W * H).reshape(H, W).astype(np.float32)


def cloud(buf, pts, col, nits, pitch, size_ref=2.5):
    """3-D points; nearer ones are brighter."""
    if len(pts) == 0:
        return
    x, y, d, ok = project(pts, pitch)
    k = np.clip((size_ref / np.maximum(d, 0.25)) ** 1.4, 0, 3.0)
    rgb = np.asarray(col, float) * (np.asarray(nits, float) * k * np.ones(len(pts)))[:, None]
    splat(buf, x[ok], y[ok], rgb[ok])


def orb(buf, cx, cy, radius, col, nits):
    r = int(radius * 5) + 2
    x0, x1, y0, y1 = max(int(cx) - r, 0), min(int(cx) + r, W), max(int(cy) - r, 0), min(int(cy) + r, H)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / radius ** 2
    a = (np.exp(-d2 * 1.6) + 0.16 * np.exp(-d2 * 0.28)) * np.clip(1 - d2 / 25.0, 0, 1) ** 2
    buf[y0:y1, x0:x1] += (a[..., None] * (np.asarray(col) * nits)).astype(np.float32)


def bloom(buf, strength=0.9):
    levels = [cv2.resize(buf, (W // 2, H // 2), interpolation=cv2.INTER_AREA)]
    for _ in range(5):
        levels.append(cv2.pyrDown(levels[-1]))
    acc = cv2.GaussianBlur(levels[-1], (0, 0), 2.0) * 0.5
    for lv, w in zip(levels[-2::-1], [0.55, 0.55, 0.6, 0.7, 0.8]):
        acc = cv2.resize(acc, (lv.shape[1], lv.shape[0])) + cv2.GaussianBlur(lv, (0, 0), 1.4) * w
    glow = cv2.resize(acc, (W, H))
    # a thin horizontal streak from only the brightest things
    q = cv2.resize(np.maximum(buf - 140.0, 0), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    streak = cv2.resize(cv2.GaussianBlur(q, (0, 0), sigmaX=60, sigmaY=0.7), (W, H))
    return buf + glow * (0.42 * strength) + streak * np.array([0.35, 0.6, 1.0], np.float32) * 0.5


# ------------------------------------------------------------------ text
_text_cache = {}


def text_mask(text, size, weight="Light", track=0.04):
    key = (text, size, weight, track)
    if key not in _text_cache:
        f = ImageFont.truetype(FONT % weight, size)
        sp = size * track
        w = int(sum(f.getlength(ch) + sp for ch in text) + 20)
        im = Image.new("L", (w, int(size * 1.6)), 0)
        d = ImageDraw.Draw(im)
        x = 10.0
        for ch in text:
            d.text((x, size * 0.2), ch, font=f, fill=255)
            x += f.getlength(ch) + sp
        _text_cache[key] = np.asarray(im, np.float32) / 255.0
    return _text_cache[key]


def put_text(buf, text, size, cx, cy, nits, col=(1, 1, 1), weight="Light", track=0.04, anchor="c"):
    m = text_mask(text, size, weight, track)
    h, w = m.shape
    x0 = int(cx - w / 2) if anchor == "c" else int(cx)
    y0 = int(cy - h / 2)
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xb <= xa or yb <= ya:
        return
    a = m[ya - y0:yb - y0, xa - x0:xb - x0][..., None]
    buf[ya:yb, xa:xb] = buf[ya:yb, xa:xb] * (1 - a) + a * (np.asarray(col, np.float32) * nits)


# ------------------------------------------------------------------ fixed fields
rng = np.random.default_rng(3)
DUST = np.column_stack([rng.uniform(-9, 9, 9000), rng.uniform(-3, 13, 9000), rng.uniform(-3, 7, 9000)])
DUST_B = rng.pareto(2.2, 9000) * 1.6 + 0.3
ORB_PTS = rng.standard_normal((2600, 3)); ORB_PTS /= np.linalg.norm(ORB_PTS, axis=1)[:, None]
ORB_R = rng.random(2600)
TRAIL_J = rng.standard_normal((70, 14, 3))
SPLASH = rng.standard_normal((220, 3))

# ------------------------------------------------------------------ exact patches: drawn after bloom, so values stay true
SHADOW_NITS = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0]


def draw_shadow(buf, t):
    a = sm(0.8, 2.0, t) * (1 - sm(6.3, 6.95, t))
    if a <= 0:
        return
    buf[690:842, 420:1500] = 0                       # clean black behind the steps
    for k, n in enumerate(SHADOW_NITS):
        x = 450 + k * 175
        buf[700:790, x:x + 145] = n * a
        put_text(buf, "%g" % n, 22, x + 72, 816, 9 * a)


def _cie_xy():
    """CIE 1931 spectral locus from the multi-lobe Gaussian fit of Wyman, Sloan and Shirley (2013)."""
    lam = np.arange(420.0, 660.1, 2.0)              # the fit drifts in the far tails: join the ends to the known limits

    def g(mu, s1, s2):
        return np.exp(-0.5 * ((lam - mu) / np.where(lam < mu, s1, s2)) ** 2)

    X = 1.056 * g(599.8, 37.9, 31.0) + 0.362 * g(442.0, 16.0, 26.7) - 0.065 * g(501.1, 20.4, 26.2)
    Y = 0.821 * g(568.8, 46.9, 40.5) + 0.286 * g(530.9, 16.3, 31.1)
    Z = 1.217 * g(437.0, 11.8, 36.0) + 0.681 * g(459.0, 26.0, 13.8)
    xy = np.column_stack([X / (X + Y + Z), Y / (X + Y + Z)])
    return np.vstack([[0.1741, 0.0050], xy, [0.7347, 0.2653]])


CHART = (470, 930, 840)                              # pixel of x=0, pixel of y=0, pixels per unit
R709 = [(0.640, 0.330), (0.300, 0.600), (0.150, 0.060)]
R2020 = [(0.708, 0.292), (0.170, 0.797), (0.131, 0.046)]
D65 = (0.3127, 0.3290)


def chart_px(xy):
    xy = np.atleast_2d(xy)
    return np.column_stack([CHART[0] + xy[:, 0] * CHART[2], CHART[1] - xy[:, 1] * CHART[2]])


def _gamut_fill():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    x = (xx - CHART[0]) / CHART[2]
    y = np.maximum((CHART[1] - yy) / CHART[2], 1e-4)
    XYZ = np.stack([x / y, np.ones_like(x), (1 - x - y) / y], axis=-1)
    M = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]], np.float32)
    rgb = XYZ @ M.T
    mask = np.zeros((H, W), np.uint8)
    cv2.fillPoly(mask, [np.round(chart_px(R709) * 16).astype(np.int32)], 255, cv2.LINE_AA, 4)
    rgb = np.clip(rgb, 0, None)
    rgb /= np.maximum(rgb.max(axis=-1, keepdims=True), 1e-6)
    return rgb.astype(np.float32), (mask.astype(np.float32) / 255)[..., None]


GAMUT_RGB, GAMUT_MASK = _gamut_fill()


def line(buf, pts, col, nits, width=2, closed=True):
    m = np.zeros((H, W), np.uint8)
    cv2.polylines(m, [np.round(pts * 16).astype(np.int32)], closed, 255, width, cv2.LINE_AA, 4)
    ys, xs = np.nonzero(m)
    a = (m[ys, xs] / 255.0)[:, None].astype(np.float32)
    buf[ys, xs] = buf[ys, xs] * (1 - a) + a * (np.asarray(col, np.float32) * nits)


def draw_gamut(buf, t):
    a = sm(28.0, 28.8, t) * (1 - sm(34.5, 35.0, t))
    if a <= 0:
        return
    buf *= 1 - a                                     # a clean plate for the chart
    for v in np.arange(0, 0.81, 0.1):
        line(buf, chart_px([(v, 0), (v, 0.85)]), (0.5, 0.6, 0.8), 2.2 * a, 1, False)
        line(buf, chart_px([(0, v), (0.8, v)]), (0.5, 0.6, 0.8), 2.2 * a, 1, False)
    line(buf, chart_px(_LOCUS), (0.8, 0.85, 0.95), 28 * a, 2)
    fill = GAMUT_MASK * (sm(30.4, 31.8, t) * a)
    buf[:] = buf * (1 - fill) + GAMUT_RGB * (55 * fill)
    line(buf, chart_px(R709), (1, 1, 1), 70 * sm(30.2, 31.0, t) * a, 2)
    names = [("red  0.640, 0.330", (1.0, 0.1, 0.1), 74, 0), ("green  0.300, 0.600", (0.1, 1.0, 0.1), 28, -22),
             ("blue  0.150, 0.060", (0.2, 0.3, 1.0), 30, 18)]
    for (txt, col, dx, dy), xy, t0 in zip(names, R709, S.GAMUT_T):
        k = sm(t0, t0 + 0.3, t) * a
        if k > 0:
            px, py = chart_px(xy)[0]
            orb(buf, px, py, 9, col, 120 * k)
            put_text(buf, txt, 24, px + dx, py + dy, 75 * k, anchor="l")
    k = sm(S.GAMUT_T[3], S.GAMUT_T[3] + 0.3, t) * a
    if k > 0:
        px, py = chart_px(D65)[0]
        orb(buf, px, py, 7, (1, 1, 1), 150 * k)
        put_text(buf, "D65 white", 22, px + 18, py + 4, 90 * k, (0.02, 0.02, 0.02), anchor="l")
    k = sm(32.6, 33.4, t) * a
    if k > 0:
        line(buf, chart_px(R2020), (0.6, 0.65, 0.75), 20 * k, 1)
        px, py = chart_px(R2020[1])[0]
        put_text(buf, "Rec.2020, the HDR10 container (outline only)", 22, px + 24, py - 6, 45 * k, anchor="l")
    cols = [("R", (1, 0, 0)), ("G", (0, 1, 0)), ("B", (0, 0, 1)), ("C", (0, 1, 1)), ("M", (1, 0, 1)), ("Y", (1, 1, 0)), ("W", (1, 1, 1))]
    k = sm(31.8, 32.8, t) * a
    for i, (nm, c) in enumerate(cols):
        x = 1220 + (i % 4) * 135
        y = 560 + (i // 4) * 150
        buf[y:y + 100, x:x + 110] = np.array(c, np.float32) * 60 * k
        put_text(buf, nm, 22, x + 55, y + 122, 45 * k)
    put_text(buf, "Rec.709 primaries and mixes", 28, 1220, 505, 70 * k, anchor="l")


_LOCUS = _cie_xy()


def draw_hdr(buf, t):
    a = sm(35.0, 35.5, t) * (1 - sm(39.2, 39.9, t))
    if a <= 0:
        return
    buf *= 1 - a
    for k, (n, t0) in enumerate(zip(S.HDR_NITS, S.HDR_T)):
        on = sm(t0, t0 + 0.2, t) * a
        x = 170 + k * 330
        buf[300:560, x:x + 260] = n * on
        put_text(buf, "%d nits" % n, 30, x + 130, 605, 70 * on)
    ramp = np.linspace(0, 1, 1580, dtype=np.float32) ** 2 * 1000
    buf[690:750, 170:1750] = ramp[None, :, None] * (sm(35.3, 36.5, t) * a)
    put_text(buf, "0", 22, 170, 780, 45 * a)
    put_text(buf, "smooth ramp to 1000 nits", 22, W / 2, 780, 45 * a)
    put_text(buf, "1000", 22, 1728, 780, 45 * a)


def draw_labels(buf, t, bar):
    for t0, t1, head, desc in S.LABELS:
        if not t0 <= t <= t1:
            continue
        a = sm(t0, t0 + 0.5, t) * (1 - sm(t1 - 0.4, t1, t))
        dim = 0.3 if head == "DYNAMIC RANGE" else 1.0
        y = bar + 52
        buf[y - 22:y + 54, 56:60] = np.array([1.0, 0.65, 0.25], np.float32) * 70 * a * dim
        put_text(buf, head, 25, 68, y - 6, 85 * a * dim, (1.0, 0.7, 0.35), "Medium", 0.16, anchor="l")
        text = desc
        if head == "ASPECT RATIO":
            text = "%s   %.2f : 1" % (desc, W / (H - 2 * bar))
        put_text(buf, text, 25, 68, y + 32, 70 * a * dim, (0.85, 0.9, 1.0), anchor="l")


# title particles
def _title_points():
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    for text, size, y, weight in [("SOFTWARE-DEFINED", 118, 400, "Thin"), ("HOME THEATRE", 118, 540, "Thin")]:
        f = ImageFont.truetype(FONT % weight, size)
        sp = size * 0.12
        w = sum(f.getlength(c) + sp for c in text) - sp
        x = (W - w) / 2
        for c in text:
            d.text((x, y - size * 0.6), c, font=f, fill=255)
            x += f.getlength(c) + sp
    mask = np.asarray(im, np.float32) / 255
    ys, xs = np.nonzero(mask > 0.5)
    k = rng.choice(len(xs), 16000, replace=False)
    return np.column_stack([xs[k], ys[k]]).astype(float), mask


TITLE, TITLE_MASK = _title_points()
T_start = np.column_stack([W / 2 + rng.standard_normal(16000) * 700, H / 2 + rng.standard_normal(16000) * 420])
T_d = rng.random(16000)
BURST_DIR = rng.standard_normal((26000, 3)); BURST_DIR /= np.linalg.norm(BURST_DIR, axis=1)[:, None]
BURST_V = rng.uniform(0.15, 1.0, 26000) ** 0.6
RAY = rng.standard_normal((420, 3)); RAY /= np.linalg.norm(RAY, axis=1)[:, None]
RAY_V = rng.uniform(0.5, 1.5, 420)
BURST_C = rng.random(26000)


def _fbm(seed, w=960, h=540):
    g = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    for o in range(6):
        n = 3 * 2 ** o
        m = max(n * h // w, 2)
        cell = np.pad(g.random((m, n)).astype(np.float32), 3, mode="wrap")
        sx, sy = w / n, h / m
        big = cv2.resize(cell, (int(round((n + 6) * sx)), int(round((m + 6) * sy))), interpolation=cv2.INTER_CUBIC)
        x0, y0 = int(round(3 * sx)), int(round(3 * sy))
        acc += big[y0:y0 + h, x0:x0 + w] / 1.8 ** o
    acc = (acc - acc.min()) / np.ptp(acc)
    return np.clip((acc - 0.5) * 2.4, 0, 1) ** 2.4


NEB = [_fbm(21), _fbm(22), _fbm(23)]


def nebula(buf, t, col_a, col_b, nits, shift=0.0):
    if nits <= 0.02:
        return
    out = np.zeros((540, 960, 3), np.float32)
    for k, (tex, col, sp) in enumerate([(NEB[0], col_a, 6.0), (NEB[1], col_b, -4.0)]):
        m = np.float32([[0.8, 0, sp * t + 140 * k], [0, 0.8, shift + 60 * k]])
        w = cv2.warpAffine(tex, m, (960, 540), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_WRAP)
        out += w[..., None] * np.array(col, np.float32)
    yy, xx = np.mgrid[0:540, 0:960]
    vig = np.clip(1.15 - ((xx - 480) / 620.0) ** 2 - ((yy - 270) / 380.0) ** 2, 0, 1).astype(np.float32)
    buf += cv2.resize(out * vig[..., None] * nits, (W, H))


NV = 60000
V_arm = rng.integers(0, 4, NV)
V_u = rng.random(NV)
V_j = rng.standard_normal((NV, 3))


def vortex(buf, t, amp, pitch):
    """Spiral arms of fine dust around the seat, stirred as the voices circle."""
    if amp <= 0:
        return
    u = t - 7.0
    r = 1.2 + 5.0 * V_u
    ang = V_arm * (np.pi / 2) + 3.6 * V_u + 0.62 * u + V_j[:, 0] * 0.16
    h = -0.9 + 0.35 * np.sin(3 * ang + 5 * V_u - u * 1.4) + V_j[:, 1] * 0.07 + 0.3 * V_u
    pts = np.column_stack([r * np.sin(ang), r * np.cos(ang), h])
    cols = np.array([[0.2, 0.55, 1.0], [0.55, 0.25, 1.0], [0.1, 0.9, 0.8], [1.0, 0.45, 0.25]])[V_arm]
    cloud(buf, pts, cols, 3.4 * amp * (1 - 0.6 * V_u), pitch, 3.0)


AU_x = rng.uniform(-6, 6, 50000)
AU_h = rng.random(50000) ** 2.2
AU_b = rng.integers(0, 3, 50000)


def aurora(buf, t, amp, pitch):
    """Curtains of light overhead: the wide ambience in the height speakers."""
    if amp <= 0:
        return
    y = 5.0 + 1.4 * AU_b + 0.8 * np.sin(0.7 * AU_x + t * 0.5 + AU_b * 2)
    base = 1.7 + 0.55 * AU_b + 0.45 * np.sin(1.3 * AU_x - t * 0.8 + AU_b)
    pts = np.column_stack([AU_x + 0.1 * np.sin(5 * AU_h + t + AU_x * 3), y, base + 2.2 * AU_h])
    ray = 0.35 + 0.65 * np.sin(AU_x * 9 + np.sin(AU_x * 3 + t) * 2 + t * 1.5) ** 2
    cols = np.array([[0.05, 1.0, 0.55], [0.1, 0.55, 1.0], [0.55, 0.2, 1.0]])[AU_b]
    cloud(buf, pts, cols, 26 * amp * ray * (1 - AU_h) ** 1.5, pitch, 4.0)


FR_n = 1400
FR = np.column_stack([rng.uniform(-6, 6, FR_n), rng.uniform(1.2, 9, FR_n), rng.random(FR_n)])


def fine_rain(buf, t, amp, pitch):
    """Picture only: faint streaks behind the drops that make a sound."""
    if amp <= 0:
        return
    for k in range(14):
        z = 3.8 - ((FR[:, 2] + (t - k * 0.006) * 0.55) % 1.0) * 4.7
        cloud(buf, np.column_stack([FR[:, 0], FR[:, 1], z]), (0.4, 0.65, 1.0), 6.0 * amp * (1 - k / 14), pitch, 3.0)


def sm(a, b, t):
    return float(S.smooth(a, b, t))


def pitch_at(t):
    return math.radians(19) * (sm(16.0, 19.6, t) - sm(26.2, 28.0, t)) + math.radians(52) * (sm(43.2, 44.3, t) - sm(44.5, 45.0, t))


def dust(buf, t, gain, pitch):
    if gain <= 0:
        return
    p = DUST.copy()
    p[:, 1] = (p[:, 1] - 0.18 * t + 3) % 16 - 3
    p[:, 0] += 0.15 * np.sin(0.2 * t + p[:, 2])
    tw = 0.7 + 0.3 * np.sin(t * 2 + DUST[:, 0] * 7)
    cloud(buf, p, (0.55, 0.68, 1.0), DUST_B * tw * gain * 2.2, pitch, 4.0)


# ------------------------------------------------------------------ scenes
def draw_origin(buf, t):
    a = sm(0.4, 2.0, t) * (1 - sm(7.0, 7.5, t))
    if a <= 0:
        return
    pulse = sum(math.exp(-max(t - t0, 0) * 2.5) * (t >= t0) for t0 in (0.6, 2.1, 3.4, 4.7, 5.6))
    grow = 1 + 2.2 * sm(5.8, 7.0, t)
    r = (0.05 + 0.016 * pulse) * grow
    th = t * 0.5
    rot = np.array([[math.cos(th), 0, math.sin(th)], [0, 1, 0], [-math.sin(th), 0, math.cos(th)]])
    wob = 1 + 0.12 * np.sin(ORB_PTS[:, 0] * 5 + t * 2) * np.sin(ORB_PTS[:, 1] * 4 - t * 1.4)
    pts = (ORB_PTS @ rot) * (r * wob * (0.75 + 0.5 * ORB_R ** 3))[:, None] + [0, 3.0, 0.15]
    cloud(buf, pts, (0.7, 0.82, 1.0), 7 * a * grow, 0.0)
    x, y, _, _ = project(np.array([[0, 3.0, 0.15]]), 0.0)
    orb(buf, x[0], y[0], (5 + 3 * pulse) * grow, (0.75, 0.86, 1.0), 45 * a * (1 + 0.5 * pulse))
    for t0 in (0.6, 2.1, 3.4, 4.7, 5.6):             # a soft ring for every note
        u = t - t0
        if 0 < u < 2.2:
            ang = np.linspace(0, 2 * np.pi, 3000)
            rr = 0.08 + 0.55 * u
            ring = np.column_stack([rr * np.cos(ang), 3.0 + 0 * ang, 0.15 + rr * np.sin(ang)])
            cloud(buf, ring, (0.4, 0.6, 1.0), 3.5 * (1 - u / 2.2) ** 2 * a, 0.0)


def draw_voices(buf, t, pitch, labels):
    if not 6.9 <= t < 21.5:
        return
    a = sm(7.0, 7.4, t) * (1 - sm(19.0, 21.4, t))
    flash = math.exp(-max(t - 7.0, 0) * 3)
    cx, cy, _, _ = project(np.array([[0, 3.0, 0.15]]), pitch)
    orb(buf, cx[0], cy[0], 40, (0.8, 0.88, 1.0), 260 * flash * a)
    glow_edge = np.zeros((2, 3))
    for i in range(S.VOICES):
        col = np.array(S.VOICE_COL[i])
        rate = 1.5 + 0.35 * i
        beat = math.exp(-5 * (((t - 7.0) * rate + i * 0.37) % 1.0))
        trail_t = np.maximum(t - np.arange(170) * 0.012, 7.0)
        path = np.array([S.voice_pos(i, u) for u in trail_t])
        age = np.arange(170) / 170.0
        pts = (path[:, None, :] + TRAIL_J[np.arange(170) % 70] * (0.005 + 0.11 * age ** 1.3)[:, None, None]).reshape(-1, 3)
        cloud(buf, pts, col, np.repeat(17 * (1 - age) ** 1.7, 14) * a, pitch)
        p = path[0]
        x, y, d, ok = project(p[None, :], pitch)
        if ok[0]:
            orb(buf, x[0], y[0], min(11 * 2.4 / max(d[0], 0.5), 30) * (1 + 0.6 * beat), col, 190 * (0.55 + 0.45 * beat) * a)
            if labels:
                put_text(buf, "V%d  az %+.0f  el %+.0f" % (i + 1, math.degrees(math.atan2(p[0], p[1])), math.degrees(math.asin(p[2] / np.linalg.norm(p)))),
                         18, x[0] + 22, y[0], 90, anchor="l")
        az = math.atan2(p[0], p[1])
        if abs(az) > math.radians(50):               # out of frame: its light spills in from that side
            k = min((abs(az) - math.radians(50)) / 0.6, 1.0) * (0.4 + beat)
            glow_edge[int(az > 0)] += col * k
    ramp = ((np.linspace(1, 0, 300) ** 3)[None, :] * np.exp(-((np.arange(H) - H / 2) / 300.0) ** 2)[:, None]).astype(np.float32)[:, :, None]
    if glow_edge[0].any():
        buf[:, :300] += ramp * (glow_edge[0] * 4 * a).astype(np.float32)
    if glow_edge[1].any():
        buf[:, -300:] += ramp[:, ::-1] * (glow_edge[1] * 4 * a).astype(np.float32)


def floor_ring(buf, center, radius, col, nits, pitch):
    ang = np.linspace(0, 2 * np.pi, 900)
    pts = np.column_stack([center[0] + radius * np.cos(ang), center[1] + radius * np.sin(ang), np.full(900, -0.9)])
    cloud(buf, pts, col, nits, pitch, 3.0)


def draw_rain(buf, t, pitch, labels):
    if not 16.0 <= t < 28.4:
        return
    a = sm(16.2, 18.4, t) * (1 - sm(26.8, 28.2, t))
    # a floor grid to catch them
    xs = np.linspace(-6, 6, 25)
    ys = np.linspace(0.8, 11, 520)
    grid = np.array([[x, y, -0.9] for x in xs for y in ys])
    cloud(buf, grid, (0.2, 0.35, 0.9), 0.9 * a, pitch, 4.0)
    for j, d in enumerate(S.DROPS):
        t0 = d[0]
        u = t - t0
        if not -0.05 < u < S.FALL + 1.4:
            continue
        col = np.array([(0.35, 0.75, 1.0), (0.6, 0.9, 1.0), (0.55, 0.5, 1.0), (0.85, 0.95, 1.0)][j % 4])
        if u <= S.FALL:
            tr = np.array([S.drop_pos(d, t - k * 0.0035) for k in range(60)])
            cloud(buf, tr, col, 24 * (1 - np.arange(60) / 60) ** 2 * a, pitch)
            x, y, dd, ok = project(tr[:1], pitch)
            if ok[0]:
                born = math.exp(-max(u, 0) * 7)
                orb(buf, x[0], y[0], min(8 * 2.4 / max(dd[0], 0.5), 20) * (1 + 2 * born), col, (130 + 420 * born) * a)
                if labels:
                    put_text(buf, "drop az %+.0f" % d[1], 16, x[0] + 12, y[0], 70, anchor="l")
        else:
            v = u - S.FALL
            p = S.drop_pos(d, t0 + S.FALL)
            for k in range(3):
                vv = v - k * 0.18
                if vv > 0:
                    floor_ring(buf, p, 0.06 + 0.75 * vv, col, 9 * max(1 - vv / 1.4, 0) ** 2 * a, pitch)
            sp = p + SPLASH * 0.12 * v + np.column_stack([0 * SPLASH[:, 0], 0 * SPLASH[:, 0], np.abs(SPLASH[:, 2]) * 0.9 * v - 1.8 * v * v])
            cloud(buf, sp, col, 10 * max(1 - v / 0.7, 0) * a, pitch)


def shock(buf, t, t0, nits, col, speed):
    u = t - t0
    if not 0 <= u < 1.6:
        return
    ang = np.linspace(0, 2 * np.pi, 5000)
    for k, r_off in enumerate((0.0, 0.05, 0.11)):
        r = 0.2 + speed * (u ** 0.7) - r_off
        if r <= 0:
            continue
        pts = np.column_stack([r * np.cos(ang), np.full(5000, 3.2), r * np.sin(ang) * 0.85])
        cloud(buf, pts, col, nits * math.exp(-u * 2.6) / (1 + k), 0.0, 3.2)


def draw_hit(buf, t, labels, pitch=0.0):
    if not 43.0 <= t < 53.5:
        return
    out = 1 - sm(51.6, 53.2, t)
    if t < S.HIT + 0.05:                             # the fly-over
        trail = np.array([S.flyover_pos(max(t - k * 0.006, 43.0)) for k in range(90)])
        age = np.arange(90) / 90
        pts = (trail[:, None, :] + TRAIL_J[np.arange(90) % 70] * (0.01 + 0.2 * age)[:, None, None]).reshape(-1, 3)
        cloud(buf, pts, (0.45, 0.75, 1.0), np.repeat(55 * (1 - age) ** 1.4, 14), pitch)
        p = trail[0]
        x, y, d, ok = project(p[None, :], pitch)
        if ok[0]:
            orb(buf, x[0], y[0], min(12 * 3 / max(d[0], 0.6), 70), (0.75, 0.9, 1.0), 450)
            if labels:
                put_text(buf, "fly-over", 20, x[0] + 40, y[0], 100, anchor="l")
        k = sm(44.2, 44.9, t)
        buf[:, :360] += (np.linspace(1, 0, 360)[None, :, None] ** 3 * np.array([2, 4, 7]) * k).astype(np.float32)
        buf[:, -360:] += (np.linspace(0, 1, 360)[None, :, None] ** 3 * np.array([2, 4, 7]) * k).astype(np.float32)
    u = t - S.HIT
    if u < 0:
        return
    pulse = sum(math.exp(-(t - tp) * 7) for tp in S.PULSES if t >= tp)
    r = (0.25 + 2.6 * (1 - math.exp(-u * 1.7)) + 0.12 * u) * (1 + 0.09 * pulse)
    th = u * 0.22
    rot = np.array([[math.cos(th), 0, math.sin(th)], [0, 1, 0], [-math.sin(th), 0, math.cos(th)]])
    swirl = np.sin(BURST_DIR[:, 0] * 4 + u * 1.3) * np.sin(BURST_DIR[:, 2] * 5 - u) * 0.18
    pts = (BURST_DIR @ rot) * (r * (BURST_V + swirl))[:, None] + [0, 3.6, 0]
    hot = math.exp(-u * 2.2)
    cols = np.where(BURST_C[:, None] < 0.55, np.array([0.2, 0.55, 1.0]), np.array([1.0, 0.42, 0.1]))
    cols = np.where((BURST_C > 0.93)[:, None], np.array([1.0, 0.95, 0.9]), cols)
    cols = cols * (1 - hot) + hot
    cloud(buf, pts, cols, (13 + 80 * hot + 12 * pulse) * out, 0.0, 3.2)
    rr = (0.2 + 3.6 * (1 - math.exp(-u * 1.1)) + 0.1 * u) * RAY_V
    seg = np.linspace(0.62, 1.0, 90)
    rays = ((RAY @ rot)[:, None, :] * (rr[:, None] * seg[None, :])[:, :, None]).reshape(-1, 3) + [0, 3.6, 0]
    rcol = np.where((np.arange(420) % 2 == 0)[:, None], np.array([0.35, 0.7, 1.0]), np.array([1.0, 0.55, 0.18]))
    cloud(buf, rays, np.repeat(rcol, 90, axis=0), np.tile((seg - 0.62) / 0.38, 420) ** 2 * (16 + 60 * hot + 14 * pulse) * math.exp(-u * 0.22) * out, 0.0, 3.2)
    x, y, _, _ = project(np.array([[0, 3.6, 0]]), 0.0)
    orb(buf, x[0], y[0], 60 + 220 * min(u * 4, 1) * hot, (1.0, 0.93, 0.85), (1000 * math.exp(-u * 5.0)))
    orb(buf, x[0], y[0], 16 + 10 * pulse, (1.0, 0.75, 0.45), (40 + 160 * pulse) * out)
    shock(buf, t, S.HIT, 90, (0.8, 0.9, 1.0), 4.2)
    for i, tp in enumerate(S.PULSES):
        shock(buf, t, tp, 26, (0.3, 0.6, 1.0) if i % 2 else (1.0, 0.5, 0.15), 3.4)


def draw_title(buf, t):
    if t < 51.4:
        return
    gone = sm(57.2, 58.8, t)
    k = np.clip((t - 51.5 - T_d * 0.9) / 1.7, 0, 1)
    k = 1 - (1 - k) ** 3
    pos = T_start * (1 - k)[:, None] + TITLE * k[:, None]
    g = np.clip(gone * 1.4 - T_d * 0.4, 0, 1)
    g = g * g
    pos = pos * (1 - g)[:, None] + np.array([W / 2, H / 2]) * g[:, None]
    solid = sm(53.6, 54.6, t) * (1 - sm(57.0, 57.7, t))
    col = np.tile(np.array([0.8, 0.88, 1.0]), (len(k), 1))
    fade = sm(51.5, 52.3, t) * (1 - sm(58.6, 59.5, t))
    splat(buf, pos[:, 0], pos[:, 1], col * (fade * (30 - 18 * solid) * (0.4 + 0.6 * k))[:, None])
    if solid > 0:
        buf += (TITLE_MASK[..., None] * np.array([0.88, 0.93, 1.0]) * 95 * solid).astype(np.float32)
    sub = sm(54.2, 55.2, t) * (1 - sm(56.9, 57.6, t))
    if sub > 0:
        put_text(buf, "decoded and rendered in software", 34, W / 2, 668, 80 * sub, (0.75, 0.82, 0.95))
        put_text(buf, "5.1.2", 40, W / 2, 748, 130 * sub, (1.0, 0.6, 0.22), "Medium", 0.25)
        buf[708, W // 2 - 220:W // 2 + 220] += np.array([0.5, 0.7, 1.0], np.float32) * 25 * sub
    last = sm(58.0, 58.6, t) * (1 - sm(59.0, 59.8, t))
    if last > 0:
        orb(buf, W / 2, H / 2, 6, (0.75, 0.86, 1.0), 120 * last)


def frame(t, labels=False, captions=True):
    buf = np.zeros((H, W, 3), np.float32)
    if 40.0 <= t < 43.0:
        pass                                         # true black, apart from one dim line
    else:
        pitch = pitch_at(t)
        dg = sm(1.0, 6.0, t) * (1 - sm(27.5, 28.5, t)) + sm(45.0, 47, t) * 0.6 * (1 - sm(58, 59.5, t))
        nebula(buf, t, (0.12, 0.3, 1.0), (0.5, 0.12, 0.8), 2.6 * sm(6.9, 9.0, t) * (1 - sm(26.0, 28.5, t)), shift=300 * pitch)
        boom = sum(math.exp(-(t - tp) * 6) for tp in S.PULSES if t >= tp)
        nebula(buf, t * 3, (0.08, 0.35, 1.0), (1.0, 0.3, 0.05), (4 + 8 * boom) * sm(45.0, 45.8, t) * (1 - sm(51.0, 53.0, t)))
        nebula(buf, t, (0.1, 0.25, 0.7), (0.3, 0.1, 0.5), 1.4 * sm(52.0, 54.0, t) * (1 - sm(57.5, 59.0, t)))
        dust(buf, t, dg, pitch)
        vortex(buf, t, sm(7.2, 9.5, t) * (1 - sm(17.0, 20.0, t)), pitch)
        aurora(buf, t, sm(15.8, 18.6, t) * (1 - sm(26.6, 28.2, t)), pitch)
        fine_rain(buf, t, sm(18.8, 22.0, t) * (1 - sm(26.4, 28.0, t)), pitch)
        if 43.0 <= t < 45.0:                         # the room's floor tips past as the camera follows the fly-over
            grid = np.array([[gx_, gy_, -0.9] for gx_ in np.linspace(-6, 6, 25) for gy_ in np.linspace(0.8, 11, 520)])
            cloud(buf, grid, (0.2, 0.4, 1.0), 2.2 * sm(43.0, 43.6, t), pitch, 4.0)
            dust(buf, t, 0.9 * sm(43.0, 43.5, t), pitch)
        draw_origin(buf, t)
        draw_voices(buf, t, pitch, labels)
        draw_rain(buf, t, pitch, labels)
        draw_hit(buf, t, labels, pitch)
        draw_title(buf, t)
        buf = bloom(buf)
    draw_shadow(buf, t)
    draw_gamut(buf, t)
    draw_hdr(buf, t)
    # scope, then the frame grows to 16:9 as the sound moves up into the heights
    open_k = sm(S.OPEN[0], S.OPEN[1], t)
    bar = int(round((H - SCOPE_H) / 2 * (1 - open_k)))
    cap_y = H - bar - 62 - int(30 * open_k)
    for t0, t1, text, _, _ in S.CAPTIONS:
        if text and t0 <= t <= t1:
            a = sm(t0, t0 + 0.5, t) * (1 - sm(t1 - 0.5, t1, t))
            quiet = 40.0 <= t0 < 43.0
            put_text(buf, text, 34 if quiet else 44, W / 2, H / 2 if quiet else cap_y, (35 if quiet else 110) * a, (0.92, 0.95, 1.0))
    if bar > 0:
        buf[:bar] = 0
        buf[H - bar:] = 0
    glow = math.sin(math.pi * open_k) if 0 < open_k < 1 else 0.0
    if glow > 0:                                     # a line of light rides each edge of the opening frame
        for y in (bar, H - bar - 2):
            y = int(np.clip(y, 0, H - 2))
            buf[y:y + 2] += np.array([0.65, 0.8, 1.0], np.float32) * 120 * glow
    draw_labels(buf, t, bar)
    if labels:
        put_text(buf, "t %05.2f   peak %4.0f nits" % (t, buf.max()), 22, 60, H - bar - 30, 90, anchor="l")
    return buf


# ------------------------------------------------------------------ encoding
M709_2020 = np.array([[0.627404, 0.329283, 0.043313], [0.069097, 0.919540, 0.011362], [0.016391, 0.088013, 0.895595]], np.float32)
_lx = np.linspace(0, 1, 65536)                      # PQ LUT, indexed by sqrt(sqrt(L / 1000))
_L = (_lx ** 4) * 1000 / 10000
_m1, _m2, _c1, _c2, _c3 = 2610 / 16384, 2523 / 4096 * 128, 3424 / 4096, 2413 / 4096 * 32, 2392 / 4096 * 32
PQ = (((_c1 + _c2 * _L ** _m1) / (1 + _c3 * _L ** _m1)) ** _m2).astype(np.float32)
PQ[0] = 0.0
DITHER = [np.random.default_rng(100 + i).random((H, W), np.float32) - 0.5 for i in range(8)]
SDITHER = SLUT = None


def to_pq_yuv(buf, n, exact=False):
    v = np.maximum(cv2.transform(buf, M709_2020), 0)
    if exact:                                        # test patches: keep the stated nits
        v = np.minimum(v, 1000)
    else:                                            # soft shoulder so nothing exceeds 1000 nits
        over = v > 700
        v[over] = 700 + 300 * (1 - np.exp(-(v[over] - 700) / 300))
    e = PQ[np.minimum(np.sqrt(np.sqrt(v / 1000.0)) * 65535 + 0.5, 65535).astype(np.int32)]
    r, g, b = e[..., 0], e[..., 1], e[..., 2]
    y = 0.2627 * r + 0.6780 * g + 0.0593 * b
    cb = cv2.resize((b - y) / 1.8814, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    cr = cv2.resize((r - y) / 1.4746, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    d = DITHER[n % 8]
    yq = np.where(y > 0, np.clip(64 + 876 * y + d + 0.5, 64, 940), 64).astype("<u2")
    cbq = np.clip(512 + 896 * cb + 0.5, 64, 960).astype("<u2")
    crq = np.clip(512 + 896 * cr + 0.5, 64, 960).astype("<u2")
    return yq.tobytes() + cbq.tobytes() + crq.tobytes(), v


def to_sdr(buf, n):
    x = np.maximum(buf, 0) / 100.0
    x = np.where(x < 0.75, x, 0.75 + 0.25 * (1 - np.exp(-(x - 0.75) / 0.9)))
    v = np.power(x, 1 / 2.4) * 255
    return np.where(x > 0, np.clip(v + DITHER[n % 8][..., None] + 0.5, 0, 255), 0).astype(np.uint8).tobytes()


def encoders(hdr, sdr):
    x265 = ("hdr10=1:hdr10-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:"
            "master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,100:log-level=error")
    a = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-s", f"{W}x{H}", "-r", str(S.FPS), "-i", "-",
                          "-c:v", "libx265", "-preset", "fast", "-crf", "19", "-x265-params", x265,
                          "-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc", "-color_range", "tv", hdr], stdin=subprocess.PIPE)
    b = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(S.FPS), "-i", "-",
                          "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "19",
                          "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", sdr], stdin=subprocess.PIPE)
    return a, b


if __name__ == "__main__":
    labels = "--labels" in sys.argv
    if "--stills" in sys.argv:
        for s in sys.argv[sys.argv.index("--stills") + 1].split(","):
            img = np.frombuffer(to_sdr(frame(float(s), labels), 0), np.uint8).reshape(H, W, 3)
            Image.fromarray(img).save("still_%05.1f.png" % float(s))
        sys.exit()
    n0, n1 = 0, int(S.DUR * S.FPS)
    if "--range" in sys.argv:
        i = sys.argv.index("--range")
        n0, n1 = int(float(sys.argv[i + 1]) * S.FPS), int(float(sys.argv[i + 2]) * S.FPS)
    a, b = encoders(sys.argv[1], sys.argv[2])
    peak = 0.0
    for n in range(n0, n1):
        buf = frame(n / S.FPS, labels)
        yuv, v = to_pq_yuv(buf, n, exact=35.0 <= n / S.FPS < 40.0)
        peak = max(peak, float(v.max()))
        a.stdin.write(yuv)
        b.stdin.write(to_sdr(buf, n))
        if n % 120 == 0:
            print("frame", n, "peak so far %.0f nits" % peak, flush=True)
    for p in (a, b):
        p.stdin.close()
        if p.wait():
            sys.exit("encoder failed")
    print("done, peak %.0f nits" % peak)
