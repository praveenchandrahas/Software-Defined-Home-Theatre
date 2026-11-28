"""Make SDR PNG previews (and an optional contact sheet) from scene-linear EXR frames (1.0 = 100 nits).

usage: python3 exr_preview.py OUT.png FRAME.exr [FRAME.exr ...]
"""
import sys
import numpy as np
import OpenEXR
from PIL import Image, ImageDraw


def read(path):
    with OpenEXR.File(path) as f:
        ch = f.channels()
        for k in ("RGB", "RGBA"):
            if k in ch:
                return np.asarray(ch[k].pixels, np.float32)[..., :3]
        return np.dstack([np.asarray(ch[c].pixels, np.float32) for c in "RGB"])


def to_sdr(x):
    """Like the player on an SDR screen: linear to 100 nits, soft shoulder above, gamma 2.4."""
    x = np.maximum(x, 0)
    x = np.where(x < 0.75, x, 0.75 + 0.25 * (1 - np.exp(-(x - 0.75) / 0.9)))
    return (np.clip(x, 0, 1) ** (1 / 2.4) * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    out, paths = sys.argv[1], sys.argv[2:]
    ims = []
    for p in paths:
        a = read(p)
        print(p, a.shape, "peak %.1f (x100 nits)" % a.max(), "mean %.4f" % a.mean())
        im = Image.fromarray(to_sdr(a[..., :3]))
        ImageDraw.Draw(im).text((8, 8), p.rsplit("/", 1)[-1], fill=(255, 200, 120))
        ims.append(im)
    w, h = ims[0].size
    cols = 2 if len(ims) > 1 else 1
    sheet = Image.new("RGB", (w * cols, h * ((len(ims) + cols - 1) // cols)), (40, 0, 40))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
    sheet.save(out)
