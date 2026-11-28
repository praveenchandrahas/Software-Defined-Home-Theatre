"""Grade test: rendered frames shown at three mastering choices, to pick the look that works at the projector's 60 nits.

Each frame is shown as A, B and C for 4 s each:
  A  as rendered (1.0 = 100 nits, highlights rolled off to 1000 nits)
  B  one stop darker below the highlights (more contrast after tone mapping)
  C  highlights capped near 400 nits (less highlight compression, brighter mid-tones after tone mapping)
Play it with the usual player (mpv-object-audio or mpv with the rig's tone-mapping settings) and note A, B or C per scene.

usage: python3 grade_test.py OUT.mkv NAME=FRAME.exr [NAME=FRAME.exr ...]
"""
import os, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import exr_preview, hdr

W, H, FPS, HOLD = 1920, 1080, 24, 4.0
FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"


def variants(nits):
    lum = nits.max(axis=-1, keepdims=True)
    # B: one stop down below 200 nits, unchanged above 600, blended between
    k = np.clip((lum - 200) / 400, 0, 1)
    b = nits * (0.5 * (1 - k) + k)
    c = hdr.shoulder(nits, peak=400.0, knee=0.6)
    return [("A", nits, 1000.0), ("B", b, 1000.0), ("C", c, 400.0)]


def label(img, text):
    m = Image.new("L", (900, 60), 0)
    ImageDraw.Draw(m).text((0, 0), text, font=ImageFont.truetype(FONT, 34), fill=255)
    a = np.asarray(m, np.float32)[..., None] / 255
    y0, x0 = H - 90, 60
    img[y0:y0 + 60, x0:x0 + 900] = img[y0:y0 + 60, x0:x0 + 900] * (1 - a) + a * 60.0   # 60 nits text
    return img


if __name__ == "__main__":
    out, items = sys.argv[1], [s.split("=", 1) for s in sys.argv[2:]]
    enc = hdr.encoder(out, maxcll=1000, maxfall=200, title="SDHT film II grade test")
    n = 0
    for name, path in items:
        nits = exr_preview.read(path)[..., :3] * 100.0
        if nits.shape[:2] != (H, W):
            nits = cv2.resize(nits, (W, H), interpolation=cv2.INTER_CUBIC)
        for tag, v, peak in variants(nits):
            frame = label(np.ascontiguousarray(v, np.float32), "%s   %s" % (name.upper(), tag))
            data = hdr.to_yuv(frame, n, peak=peak if tag == "C" else 1000.0)
            for _ in range(int(HOLD * FPS)):
                enc.stdin.write(data)
                n += 1
    enc.stdin.close()
    assert enc.wait() == 0
    print("wrote", out, n / FPS, "s")
