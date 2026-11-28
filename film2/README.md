# SDHT film II (work in progress)

A 100 second showcase of the whole rig: picture, 5.1.2 sound, mpv and CamillaDSP. The plan, storyboard and
decisions are in the project notes; this folder holds the code. Nothing here is a finished film yet.

- `blender/`: scenes written as Python scripts for Blender (`bpy`), rendered to scene-linear EXR (1.0 = 100 nits).
  `python3 blender/render.py storm --frames 20 --res 640x360 --samples 32 --out out` renders one small frame.
- `tools/exr_preview.py`: SDR previews of EXR frames. `tools/fetch_stock.py`: downloads and checks the stock clips.
- `stock.json`: the stock clips (Pexels License). Only the list is in the repository, not the clips.
- `.github/workflows/film2.yml`: renders on GitHub's runners (milestone M0: one timed frame per scene and engine). It runs when `render.json` changes.
- `rig/rattle_sweep.py`: bass bursts at rising frequency and level, to find what rattles. `rig/grade_test.py`: frames at three mastering choices, to pick the grade for the projector.
- `tools/hdr.py`: HDR10 encoding (linear nits to PQ, BT.2020, x265).

Status (2026-11-28): M0, feasibility. Scenes are rough prototypes for timing, not the film's look.
