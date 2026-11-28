"""Download the stock clips in stock.json, check them, and report on each.

usage: python3 fetch_stock.py stock.json --out DIR [--report-only]
For each clip: sha256 (checked when the manifest has one), resolution, frame rate, duration,
three thumbnails, and the most flashes in any one second (a rough check against the
three-flashes-a-second guideline, from the frame-average brightness).
"""
import argparse, hashlib, json, os, subprocess, sys, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) sdht-film2-build"


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
        return r.geturl()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def probe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate,pix_fmt,color_transfer,codec_name:format=duration",
                                   "-of", "json", path], capture_output=True, text=True, check=True).stdout)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {"width": s["width"], "height": s["height"], "fps": round(int(num) / int(den), 3), "codec": s["codec_name"],
            "pix_fmt": s["pix_fmt"], "transfer": s.get("color_transfer"), "duration": float(j["format"]["duration"])}


def brightness(path):
    """Average brightness of each frame, 0 to 1 (video levels, not light in the room)."""
    import numpy as np
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=160:90,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(out, np.uint8)
    return a[: len(a) // 14400 * 14400].reshape(-1, 14400).mean(axis=1) / 255.0


def flashes(y, fps):
    """Count rises and falls of at least 10% of full scale in the frame average; a flash is a pair."""
    import numpy as np
    ext = [0]
    for i in range(1, len(y)):
        if abs(y[i] - y[ext[-1]]) >= 0.10:
            ext.append(i)
    trans = np.array(ext[1:])
    win = int(round(fps))
    best = 0
    for i in range(len(y)):
        best = max(best, int(((trans >= i) & (trans < i + win)).sum()))
    return best / 2.0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--out", default="stock")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    clips = json.load(open(a.manifest))["clips"]
    report, bad = [], 0
    for c in clips:
        path = os.path.join(a.out, "%d.mp4" % c["id"])
        r = {"id": c["id"], "use": c["use"]}
        try:
            if not os.path.exists(path):
                r["final_url"] = download("https://www.pexels.com/download/video/%d/" % c["id"], path)
            r["sha256"] = sha256(path)
            if c.get("sha256") and c["sha256"] != r["sha256"]:
                r["error"] = "checksum differs from the manifest"
                bad += 1
            r.update(probe(path))
            y = brightness(path)
            r["max_flashes_per_s"] = flashes(y, r["fps"])
            for k, frac in enumerate((0.1, 0.5, 0.9)):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(r["duration"] * frac), "-i", path, "-frames:v", "1",
                                "-vf", "scale=640:-2", os.path.join(a.out, "%d_%d.jpg" % (c["id"], k))], check=True)
        except Exception as e:  # report and continue with the next clip
            r["error"] = "%s: %s" % (type(e).__name__, e)
            bad += 1
        print(json.dumps(r), flush=True)
        report.append(r)
    json.dump(report, open(os.path.join(a.out, "report.json"), "w"), indent=1)
    sys.exit(1 if bad else 0)
