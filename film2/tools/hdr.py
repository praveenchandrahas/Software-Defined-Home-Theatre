"""HDR10 encoding: linear BT.709 light in nits -> PQ, BT.2020, 10-bit 4:2:0, piped to x265."""
import subprocess
import numpy as np
import cv2

M709_2020 = np.array([[0.627404, 0.329283, 0.043313], [0.069097, 0.919540, 0.011362], [0.016391, 0.088013, 0.895595]], np.float32)
_m1, _m2, _c1, _c2, _c3 = 2610 / 16384, 2523 / 4096 * 128, 3424 / 4096, 2413 / 4096 * 32, 2392 / 4096 * 32


def pq(nits):
    l = np.clip(nits / 10000.0, 0, 1) ** _m1
    return ((_c1 + _c2 * l) / (1 + _c3 * l)) ** _m2


def shoulder(v, peak=1000.0, knee=0.7):
    """Values above knee*peak roll off smoothly so nothing exceeds peak."""
    k = knee * peak
    out = v.copy()
    m = v > k
    out[m] = k + (peak - k) * (1 - np.exp(-(v[m] - k) / (peak - k)))
    return out


def to_yuv(nits, n, peak=1000.0):
    """nits: H x W x 3 linear BT.709. Returns planar 10-bit YUV 4:2:0 bytes (limited range)."""
    h, w = nits.shape[:2]
    v = shoulder(np.maximum(cv2.transform(nits.astype(np.float32), M709_2020), 0), peak)
    e = pq(v).astype(np.float32)
    r, g, b = e[..., 0], e[..., 1], e[..., 2]
    y = 0.2627 * r + 0.6780 * g + 0.0593 * b
    cb = cv2.resize((b - y) / 1.8814, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    cr = cv2.resize((r - y) / 1.4746, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    d = np.random.default_rng(100 + n % 8).random((h, w), np.float32) - 0.5
    yq = np.where(y > 0, np.clip(64 + 876 * y + d + 0.5, 64, 940), 64).astype("<u2")
    cbq = np.clip(512 + 896 * cb + 0.5, 64, 960).astype("<u2")
    crq = np.clip(512 + 896 * cr + 0.5, 64, 960).astype("<u2")
    return yq.tobytes() + cbq.tobytes() + crq.tobytes()


def encoder(path, w=1920, h=1080, fps=24, maxcll=1000, maxfall=100, crf=18, audio=None, title=None):
    x265 = ("hdr10=1:hdr10-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:"
            "master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):"
            "max-cll=%d,%d:log-level=error" % (maxcll, maxfall))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
    if audio:
        cmd += ["-i", audio, "-map", "0:v", "-map", "1:a", "-c:a", "flac", "-sample_fmt", "s32", "-bits_per_raw_sample", "24"]
    cmd += ["-c:v", "libx265", "-preset", "medium", "-crf", str(crf), "-x265-params", x265,
            "-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc", "-color_range", "tv"]
    if title:
        cmd += ["-metadata", "title=" + title]
    return subprocess.Popen(cmd + [path], stdin=subprocess.PIPE)
