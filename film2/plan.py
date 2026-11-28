"""Split the scenes into render jobs for CI. Prints a JSON matrix: one entry per chunk of frames.

usage: python3 plan.py render.json
"""
import json, sys
import timeline as T

cfg = json.load(open(sys.argv[1]))
jobs = []
for name, (a, b, engine) in T.SCENES.items():
    n = int(round((b - a) * T.FPS))
    step = cfg["chunk"][engine]
    for f0 in range(1, n + 1, step):
        f1 = min(n, f0 + step - 1)
        jobs.append({"scene": name, "engine": engine, "frames": "%d:%d" % (f0, f1), "id": "%s-%04d" % (name, f0),
                     "res": cfg["res"], "samples": cfg["samples"][engine], "codec": cfg.get("codec", "ZIP")})
print(json.dumps({"include": jobs}))
if cfg.get("reuse_run"):
    print("frames come from run %s; no rendering" % cfg["reuse_run"], file=sys.stderr)
