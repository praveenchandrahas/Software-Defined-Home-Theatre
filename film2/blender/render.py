"""Render frames of one scene to EXR.

usage: python3 render.py SCENE --frames A[:B] --out DIR [--res 1920x1080] [--samples 128]
Prints one JSON line per frame with the time it took.
"""
import argparse, importlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import common

ap = argparse.ArgumentParser()
ap.add_argument("scene")
ap.add_argument("--frames", default="1")
ap.add_argument("--out", default="out")
ap.add_argument("--res", default="1920x1080")
ap.add_argument("--samples", type=int, default=128)
ap.add_argument("--threads", type=int, default=0)
ap.add_argument("--engine", default="cycles", choices=["cycles", "eevee"])
ap.add_argument("--codec", default="ZIP", choices=["ZIP", "DWAA", "PIZ"])
ap.add_argument("--resume", action="store_true")
a = ap.parse_args()

mod = importlib.import_module("scenes." + a.scene)
sc = common.reset()
res = tuple(int(v) for v in a.res.split("x"))
if a.engine == "cycles":
    common.cycles(sc, res, a.samples, **getattr(mod, "CYCLES", {}))
else:
    common.eevee(sc, res, a.samples)
mod.build(sc)
sc.render.image_settings.exr_codec = a.codec
if a.threads:
    sc.render.threads_mode = "FIXED"
    sc.render.threads = a.threads
f0, _, f1 = a.frames.partition(":")
os.makedirs(a.out, exist_ok=True)
for f in range(int(f0), int(f1 or f0) + 1):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(a.out, "%s_%s_%04d.exr" % (a.scene, a.engine, f))
    if a.resume and os.path.exists(sc.render.filepath):
        continue
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(json.dumps({"scene": a.scene, "frame": f, "seconds": round(time.time() - t, 1), "res": a.res,
                      "samples": a.samples, "engine": a.engine}), flush=True)
