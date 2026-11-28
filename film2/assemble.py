"""Put the film together: rendered EXR frames, stock clips and the mix -> HDR10 and SDR MKV files, with chapters,
plus a report (flash check, which frames were missing).

usage: python3 assemble.py --frames DIR --stock DIR --audio MIX.wav --out NAME [--allow-missing] [--width 1920]
Writes NAME-hdr10.mkv, NAME-sdr.mkv and NAME-report.json.
"""
import argparse, glob, json, os, subprocess, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import timeline as T                      # noqa: E402
import exr_preview, hdr                   # noqa: E402

CHAPTERS = [(0.0, "Black"), (8.0, "Echo"), (18.0, "Rain"), (30.0, "Storm"), (42.0, "One drop"), (50.0, "Canyon"),
            (65.0, "Orbit"), (75.0, "Silence"), (78.0, "Pressure wave"), (90.0, "Title")]
STOCK_GAIN = 0.55          # stock is SDR: its white lands at 55 nits, below the rendered highlights
SDR_PEAK = 100.0


def stock_frames(path, t_in, dur, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t_in), "-i", path, "-t", str(dur), "-vf",
                          f"fps={T.FPS},scale={w}:{h}:flags=lanczos,format=rgb24", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def stock_to_nits(rgb8):
    v = (rgb8.astype(np.float32) / 255.0) ** 2.4 * 100.0 * STOCK_GAIN
    v = np.maximum(v - 0.15, 0)                                     # a little deeper black
    return v * np.array([0.92, 0.98, 1.08], np.float32)             # cooler, to sit with the CG


def to_sdr8(nits):
    x = np.maximum(nits / SDR_PEAK, 0)
    x = np.where(x < 0.75, x, 0.75 + 0.25 * (1 - np.exp(-(x - 0.75) / 0.9)))
    return (np.clip(x, 0, 1) ** (1 / 2.4) * 255 + 0.5).astype(np.uint8)


def flash_count(lum, fps):
    """Harding-style: a flash is a pair of opposing changes of >= 20 nits where the darker state is below 160 nits.
    Returns the most flashes in any one second for this luminance series."""
    ext = [0]
    for i in range(1, len(lum)):
        a, b = lum[ext[-1]], lum[i]
        if abs(b - a) >= 20 and min(a, b) < 160:
            ext.append(i)
    tr = np.array(ext[1:])
    best = 0
    for i in range(len(lum)):
        best = max(best, int(((tr >= i) & (tr < i + fps)).sum()))
    return best / 2.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--stock", default="stock")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-missing", action="store_true")
    ap.add_argument("--width", type=int, default=1920)
    a = ap.parse_args()
    W = a.width
    H = W * 9 // 16
    nframes = int(T.DUR * T.FPS)
    files = {}
    for p in glob.glob(os.path.join(a.frames, "**", "*.exr"), recursive=True):
        base = os.path.basename(p)[:-4]
        scene, engine, num = base.rsplit("_", 2)
        files[(scene, int(num))] = p
    stock = {}
    for name, sid, s0, s1, t_in in T.STOCK:
        p = os.path.join(a.stock, "%d.mp4" % sid)
        if os.path.exists(p):
            stock[name] = (s0, stock_frames(p, t_in, s1 - s0 + 0.1, W, H))
        elif not a.allow_missing:
            sys.exit("missing stock clip %s" % p)
    meta = os.path.join(os.path.dirname(os.path.abspath(a.out)) or ".", "chapters.txt")
    with open(meta, "w") as f:
        f.write(";FFMETADATA1\ntitle=SDHT film II (animatic)\n")
        for i, (t0, title) in enumerate(CHAPTERS):
            t1 = CHAPTERS[i + 1][0] if i + 1 < len(CHAPTERS) else T.DUR
            f.write("[CHAPTER]\nTIMEBASE=1/1000\nSTART=%d\nEND=%d\ntitle=%s\n" % (t0 * 1000, t1 * 1000, title))
    enc_h = hdr.encoder("tmp-hdr.mkv", W, H, T.FPS, maxcll=1000, maxfall=120)
    enc_s = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(T.FPS),
                              "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                              "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "tmp-sdr.mkv"],
                             stdin=subprocess.PIPE)
    missing, lum_full, lum_q, peaks = [], [], [], []
    for n in range(nframes):
        t = n / T.FPS
        img = np.zeros((H, W, 3), np.float32)
        for name, (s0, s1, _) in T.SCENES.items():
            if s0 <= t < s1:
                f = T.scene_frame(name, t)
                p = files.get((name, f))
                if p is None:
                    missing.append((name, f))
                    if not a.allow_missing:
                        sys.exit("missing frame %s %d" % (name, f))
                else:
                    x = exr_preview.read(p)[..., :3] * 100.0
                    img = cv2.resize(x, (W, H), interpolation=cv2.INTER_CUBIC) if x.shape[1] != W else x
                    img = np.maximum(img, 0)
        for name, sid, s0, s1, _ in T.STOCK:
            if s0 <= t < s1 and name in stock:
                k = min(int(round((t - s0) * T.FPS)), len(stock[name][1]) - 1)
                img = stock_to_nits(stock[name][1][k])
        if T.FADE_OUT[0] <= t < T.FADE_OUT[1]:
            img *= (1 - (t - T.FADE_OUT[0]) / (T.FADE_OUT[1] - T.FADE_OUT[0])) ** 2
        bar = int(round((H - W / T.aspect(t)) / 2))
        if bar > 0:
            img[:bar] = 0
            img[H - bar:] = 0
        y = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        lum_full.append(float(y.mean()))
        lum_q.append([float(q.mean()) for q in (y[:H // 2, :W // 2], y[:H // 2, W // 2:], y[H // 2:, :W // 2], y[H // 2:, W // 2:])])
        peaks.append(float(y.max()))
        enc_h.stdin.write(hdr.to_yuv(img, n))
        enc_s.stdin.write(to_sdr8(img).tobytes())
    for e in (enc_h, enc_s):
        e.stdin.close()
        assert e.wait() == 0
    for tmp, final in (("tmp-hdr.mkv", a.out + "-hdr10.mkv"), ("tmp-sdr.mkv", a.out + "-sdr.mkv")):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", a.audio, "-i", meta, "-map", "0:v", "-map", "1:a",
                        "-map_metadata", "2", "-map_chapters", "2", "-c:v", "copy", "-c:a", "flac", "-sample_fmt", "s32",
                        "-bits_per_raw_sample", "24", "-channel_layout", "7.1", final], check=True)
        os.remove(tmp)
    lq = np.array(lum_q)
    report = {"frames": nframes, "missing": len(missing), "missing_first": missing[:10],
              "flashes_per_s_full": flash_count(np.array(lum_full), T.FPS),
              "flashes_per_s_quarter": max(flash_count(lq[:, k], T.FPS) for k in range(4)),
              "peak_nits": round(max(peaks), 1), "mean_nits_by_second": [round(float(np.mean(lum_full[i:i + T.FPS])), 2) for i in range(0, nframes, T.FPS)]}
    json.dump(report, open(a.out + "-report.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != "mean_nits_by_second"}))


if __name__ == "__main__":
    main()
