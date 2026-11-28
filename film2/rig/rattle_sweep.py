"""Rattle sweep: short bass bursts at rising frequency and level, to find what rattles in the room.

Play it through the normal film chain (CamillaDSP on, volume at the usual film position).
Note the step number on screen whenever something buzzes or rattles; the steps are also listed in rattle-steps.csv.
Steady tones at -14 dBFS did not reproduce the rattle before (status page), so these are bursts up to -6 dBFS,
shaped like the film's hits.

usage: python3 rattle_sweep.py OUT.mkv
"""
import csv, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FS, FPS, W, H = 48000, 24, 1920, 1080
FONT = "/usr/share/fonts/opentype/inter/Inter-%s.otf"
FILE_ORDER = ["FL", "FR", "C", "LFE", "TFL", "TFR", "SL", "SR"]
FREQS = [round(30 * 2 ** (k / 12), 1) for k in range(21)]          # 30 to 99 Hz, 1/12 octave
LEVELS = [-21, -15, -9, -6]                                          # peak dBFS of each burst
BURST, GAP, PER = 0.35, 0.05, 3                                      # three bursts per frequency
STEP = PER * (BURST + GAP) + 0.4
INTRO = 6.0
PAIRS = [("LFE", ["LFE"]), ("FRONT + HEIGHTS", ["FL", "FR", "TFL", "TFR"])]


def burst(f, db):
    n = int(BURST * FS)
    t = np.arange(n) / FS
    return np.sin(2 * np.pi * f * t) * np.hanning(n) * 10 ** (db / 20)


def plan():
    steps, t = [], INTRO
    for name, chans in PAIRS:
        levels = LEVELS if name == "LFE" else LEVELS[:3]
        for li, db in enumerate(levels):
            for f in FREQS:
                steps.append({"step": len(steps) + 1, "start_s": round(t, 2), "channels": name, "hz": f, "dbfs": db})
                t += STEP
            t += 1.5
    return steps, t + 2.0


def font(size, weight="Light"):
    return ImageFont.truetype(FONT % weight, size)


def card(lines):
    im = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 330
    for text, size, col in lines:
        f = font(size, "Medium" if size > 80 else "Light")
        d.text((W / 2, y), text, font=f, fill=col, anchor="mm")
        y += size * 1.5
    return im.tobytes()


if __name__ == "__main__":
    out = sys.argv[1]
    steps, dur = plan()
    n = int(dur * FS)
    x = np.zeros((n, 8))
    for s in steps:
        names = dict(PAIRS)[s["channels"]]
        b = burst(s["hz"], s["dbfs"] - (20 * np.log10(len(names)) if len(names) > 1 else 0))  # same total bass level
        for k in range(PER):
            i0 = int((s["start_s"] + k * (BURST + GAP)) * FS)
            for nm in names:
                x[i0:i0 + len(b), FILE_ORDER.index(nm)] += b
    d = np.clip(np.round(x * 8388607), -8388608, 8388607).astype("<i4")
    with wave.open("rattle.wav", "wb") as w:
        w.setnchannels(8); w.setsampwidth(3); w.setframerate(FS)
        w.writeframes(d.reshape(-1, 1).view(np.uint8)[:, :3].tobytes())
    with open("rattle-steps.csv", "w", newline="") as f:
        cw = csv.DictWriter(f, fieldnames=list(steps[0])); cw.writeheader(); cw.writerows(steps)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-i", "rattle.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                            "-tune", "stillimage", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", "-c:a", "flac", "-sample_fmt", "s32", "-bits_per_raw_sample", "24",
                            "-channel_layout", "7.1", "-metadata", "title=SDHT film II rattle sweep", out], stdin=subprocess.PIPE)
    cache = {}
    for fr in range(int(dur * FPS)):
        t = fr / FPS
        cur = [s for s in steps if s["start_s"] <= t < s["start_s"] + STEP]
        if t < INTRO:
            key = ("intro",)
            lines = [("RATTLE SWEEP", 90, (255, 180, 90)), ("bass bursts, 30 to 99 Hz, rising level", 40, (200, 210, 230)),
                     ("volume at the usual film position, CamillaDSP on", 34, (150, 160, 180)),
                     ("note the step number whenever anything buzzes", 34, (150, 160, 180))]
        elif cur:
            s = cur[0]
            key = (s["step"],)
            lines = [("STEP %d" % s["step"], 120, (255, 255, 255)), ("%s   %.1f Hz   %d dBFS" % (s["channels"], s["hz"], s["dbfs"]), 54, (255, 180, 90)),
                     ("of %d" % len(steps), 34, (120, 130, 150))]
        else:
            key = ("gap",)
            lines = [("", 10, (0, 0, 0))]
        if key not in cache:
            cache[key] = card(lines)
        enc.stdin.write(cache[key])
    enc.stdin.close()
    assert enc.wait() == 0
    print("wrote", out, "%.0f s," % dur, len(steps), "steps")
