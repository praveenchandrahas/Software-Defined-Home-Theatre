"""A short rig check: each speaker in turn, one path, the sub, level steps, a flash with a click, HDR brightness steps."""
import subprocess, math
import numpy as np
import score as S
import audio as A
import video as V

FS, FPS = S.FS, S.FPS
DUR = 26.0
N = int(DUR * FS)
rng = np.random.default_rng(1)

ORDER = [("FL", "FRONT LEFT"), ("C", "CENTRE"), ("FR", "FRONT RIGHT"), ("SR", "SURROUND RIGHT"), ("SL", "SURROUND LEFT"),
         ("TFL", "HEIGHT LEFT"), ("TFR", "HEIGHT RIGHT"), ("LFE", "SUB (LFE, 60 Hz)")]
STEP = 1.4                                       # speakers: 0 - 11.2 s
PATH = (11.2, 15.2)                              # one lap FL -> FR -> SR -> SL, rising to the heights
LEVELS = (15.6, [-40, -30, -20, -12])            # 0.9 s each
SYNC = [20.0, 21.0]
NITS = (22.0, [0, 0.5, 2, 10, 50, 100, 200, 400, 700, 1000])


def pink(d):
    w = np.fft.rfft(rng.standard_normal(int(d * FS)))
    f = np.fft.rfftfreq(int(d * FS), 1 / FS)
    w /= np.sqrt(np.maximum(f, 20))
    x = np.fft.irfft(w, int(d * FS))
    x = A.filt(x, "bandpass", [200, 8000], 2)
    return x / np.sqrt(np.mean(x ** 2))


def path_pos(t):
    u = (t - PATH[0]) / (PATH[1] - PATH[0])
    az = -30 + 360 * u
    return S.polar(az, 55 * math.sin(math.pi * u) ** 2, 2.4)


def sound():
    x = np.zeros((N, 8))
    for i, (nm, _) in enumerate(ORDER):
        for k in (0.1, 0.7):                     # two bursts per speaker
            n = int(0.45 * FS)
            if nm == "LFE":
                s = np.sin(2 * np.pi * 60 * np.arange(n) / FS) * A.env(n, 0.02, 0.05) * 10 ** (-18 / 20)
            else:
                s = pink(0.45) * A.env(n, 0.01, 0.05) * 10 ** (-26 / 20)
            A_direct(x, s, i * STEP + k, nm)
    n = int((PATH[1] - PATH[0]) * FS)
    s = pink(PATH[1] - PATH[0]) * A.env(n, 0.1, 0.2) * 10 ** (-24 / 20)
    i0 = int(PATH[0] * FS)
    for a in range(0, n, 512):
        b = min(a + 512, n)
        g0, g1 = A.vb.gains(path_pos(PATH[0] + a / FS)), A.vb.gains(path_pos(PATH[0] + b / FS))
        r = np.linspace(0, 1, b - a, endpoint=False)[:, None]
        x[i0 + a:i0 + b, :7] += s[a:b, None] * (g0 * (1 - r) + g1 * r)
    for k, db in enumerate(LEVELS[1]):           # 1 kHz on the centre, peak level as shown
        n = int(0.7 * FS)
        A_direct(x, np.sin(2 * np.pi * 1000 * np.arange(n) / FS) * A.env(n, 0.01, 0.02) * 10 ** (db / 20), LEVELS[0] + 0.9 * k, "C")
    for t in SYNC:
        n = int(0.02 * FS)
        A_direct(x, np.sin(2 * np.pi * 2000 * np.arange(n) / FS) * 10 ** (-12 / 20), t, "C")
    return x


def A_direct(x, s, t0, nm):
    i0 = int(round(t0 * FS))
    x[i0:i0 + len(s), A.IDX[nm]] += s


def picture(t):
    buf = np.zeros((V.H, V.W, 3), np.float32)

    def label(a, b=None):
        V.put_text(buf, a, 64, V.W / 2, 480, 100, weight="Medium")
        if b:
            V.put_text(buf, b, 30, V.W / 2, 580, 70, (0.7, 0.8, 1.0))

    if t < 11.2:
        i = int(t // STEP)
        label(ORDER[i][1], "speaker %d of 8" % (i + 1))
    elif t < PATH[1]:
        p = path_pos(t)
        label("ONE LAP", "azimuth %+.0f   elevation %.0f" % (math.degrees(math.atan2(p[0], p[1])), math.degrees(math.asin(p[2] / np.linalg.norm(p)))))
    elif LEVELS[0] <= t < LEVELS[0] + 3.6:
        k = int((t - LEVELS[0]) // 0.9)
        label("CENTRE  %d dBFS" % LEVELS[1][k], "1 kHz level steps")
    elif 19.2 <= t < 22.0:
        if any(s <= t < s + 1 / FPS - 1e-9 for s in SYNC):
            buf[:] = 200
        else:
            V.put_text(buf, "SYNC: flash and click together", 36, V.W / 2, 540, 70)
    elif t >= NITS[0]:
        V.put_text(buf, "BRIGHTNESS STEPS (nits in the master)", 34, V.W / 2, 220, 70)
        w = V.W // len(NITS[1])
        for k, n in enumerate(NITS[1]):
            buf[380:700, k * w + 8:(k + 1) * w - 8] = n
            V.put_text(buf, "%g" % n, 30, k * w + w / 2, 760, 70)
    return buf


if __name__ == "__main__":
    x = sound()
    A.write24("test.wav", A.to_file_order(x))
    hdr, sdr = V.encoders("test_v.mkv", "test_sdr_v.mkv")
    for n in range(int(DUR * FPS)):
        buf = picture(n / FPS)
        hdr.stdin.write(V.to_pq_yuv(buf, n, exact=True)[0])
        sdr.stdin.write(V.to_sdr(buf, n))
    for p in (hdr, sdr):
        p.stdin.close()
        assert p.wait() == 0
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "test_v.mkv", "-i", "test.wav", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "flac", "-sample_fmt", "s32", "-bits_per_raw_sample", "24",
                    "-channel_layout", "7.1", "-metadata", "title=SDHT intro rig test", "sdht-intro-rigtest.mkv"], check=True)
    print("wrote sdht-intro-rigtest.mkv")
