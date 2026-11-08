#!/usr/bin/env python3
"""Draws docs/img/ecosystem-map.png and .svg: the whole project on one page, every component placed in the repository that holds it.

Run from anywhere:  python3 tools/make-ecosystem-map.py
The names and roles come from the README's repository table; edit the lists below when a repository changes.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "img")

INK, MUTED, BG = "#1b2430", "#5b6674", "#fbfaf7"
# One colour per repository; every box also carries the repository name in text, so colour is never the only cue.
REPO = {
    "mpv-object-audio": "#2f7fb8",
    "linux-theater-dsp": "#c46a1a",
    "Roomtone": "#2e8b57",
    "seekthumbs": "#8a5cb5",
    "mpv-shelf": "#b5527a",
    "Spatial-Lab": "#b08a00",
    "sdht": "#5b6674",
}

fig, ax = plt.subplots(figsize=(16, 12.4), dpi=130)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 160)
ax.set_ylim(-29, 100)
ax.axis("off")


def box(x, y, w, h, title, lines=(), repo=None, ext=False, dashed=False, tsize=9.8):
    col = REPO[repo] if repo else "#8a929c"
    face = "#ffffff" if not ext else "#eeeeea"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=1.2", linewidth=1.8,
                                edgecolor=col, facecolor=face, linestyle="--" if dashed else "-"))
    ax.text(x + w / 2, y + h - 2.2, title, ha="center", va="top", fontsize=tsize, fontweight="bold", color=INK)
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, y + h - 5.4 - 2.8 * i, ln, ha="center", va="top", fontsize=8.0, color=MUTED)


def group(x, y, w, h, repo, caption):
    col = REPO[repo]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=1.6", linewidth=2.2,
                                edgecolor=col, facecolor=col + "10"))
    ax.text(x + 1.6, y + h - 1.2, repo, ha="left", va="top", fontsize=11.5, fontweight="bold", color=col)
    ax.text(x + w - 1.6, y + h - 1.5, caption, ha="right", va="top", fontsize=8.2, color=col, style="italic")


def arrow(x1, y1, x2, y2, dashed=False, color=INK, label=None, lx=None, ly=None, ha="left"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13, linewidth=1.6, color=color,
                                 linestyle="--" if dashed else "-"))
    if label:
        ax.text(lx if lx is not None else (x1 + x2) / 2 + 1, ly if ly is not None else (y1 + y2) / 2, label,
                ha=ha, va="center", fontsize=8, color=color)


ax.text(2, 98, "One project, seven repositories", fontsize=20, fontweight="bold", color=INK, va="top")
ax.text(2, 93.4, "Each coloured frame is one GitHub repository and holds the parts drawn inside it. Grey boxes are other people's software or hardware.",
        fontsize=9.2, color=MUTED, va="top")

# ---------------- playback chain (top band) ----------------
ax.text(2, 87.2, "PLAYBACK: film file to speakers", fontsize=9.5, fontweight="bold", color=MUTED)
box(2, 62, 18, 18, "Media library", ["read-only mount", "(rclone or debrid)", "Atmos / TrueHD"], ext=True)

group(23, 56, 38, 28, "mpv-object-audio", "installer + wrapper")
box(25, 60, 15.5, 16, "mpv-atmos", ["the wrapper:", "opens the player", "with 8 outputs"], repo="mpv-object-audio")
box(43, 60, 16, 16, "Decode + render", ["harletty-bridge,", "Omniphony, patched", "mpv (their software)"], ext=True, tsize=9.2)

group(65, 56, 46, 28, "linux-theater-dsp", "routing, profiles, upmix")
box(67, 60, 13, 16, "theater-route", ["links the player", "to CamillaDSP", "(PipeWire)"], repo="linux-theater-dsp", tsize=9.0)
box(82, 60, 13, 16, "upmix engine", ["stereo / 5.1", "to 5.1.2"], repo="linux-theater-dsp", tsize=9.0, dashed=True)
box(97, 60, 12.5, 16, "set-eq.py", ["writes the", "CamillaDSP", "profiles"], repo="linux-theater-dsp", tsize=9.0)

box(115, 62, 19, 18, "CamillaDSP", ["delays, trims,", "bass EQ, bass", "management"], ext=True)
box(138, 71, 20, 11, "USB 7.1 interface", ["8 analogue outputs"], ext=True, tsize=9.2)
box(138, 56, 20, 11, "Z906 + height amp", ["5.1 bed + sub, 2 ceiling"], ext=True, tsize=9.2)

arrow(20, 71, 25, 71)
arrow(40.5, 68, 43, 68)
arrow(59, 68, 67, 68)
arrow(80, 68, 82, 68)
arrow(95, 68, 97, 68)
arrow(109.5, 71, 115, 71)
arrow(134, 73, 138, 76)
arrow(148, 71, 148, 67)

# ---------------- library tools (bottom left, two groups side by side) ----------------
ax.text(2, 51.4, "LIBRARY TOOLS", fontsize=9.5, fontweight="bold", color=MUTED)
group(2, 3, 26, 44, "seekthumbs", "thumbnails")
box(4, 28, 22, 12, "Builder", ["one set per film", "(on play: opt-in)"], repo="seekthumbs", tsize=9.4)
box(4, 8, 22, 12, "mpv viewer", ["preview on the", "seek bar"], repo="seekthumbs", tsize=9.4)
arrow(15, 28, 15, 20)

group(31, 3, 26, 44, "mpv-shelf", "film browser")
box(33, 14, 22, 24, "Browser in mpv", ["poster grid,", "Continue Watching,", "search, title pages", "", "plays through the", "same mpv-atmos"], repo="mpv-shelf", tsize=9.4)

arrow(15, 47, 28, 56, dashed=True, color=REPO["seekthumbs"])
arrow(44, 47, 38, 56, dashed=True, color=REPO["mpv-shelf"])

# ---------------- measurement loop (bottom right) ----------------
ax.text(62, 51.4, "MEASUREMENT: tune the room, then re-measure", fontsize=9.5, fontweight="bold", color=MUTED)
group(60, 3, 98, 46, "Roomtone", "measure, propose, apply, verify")
box(62, 24, 18, 15, "Microphone", ["at the listening", "seat (Dayton", "iMM-6S here)"], ext=True, tsize=9.4)
box(84, 24, 22, 15, "autocal", ["plays sweeps through", "the live chain; proposes", "delays, trims, bass cuts"], repo="Roomtone", tsize=9.8)
box(110, 24, 20, 15, "room.json", ["the applied values:", "backup + 60 s trial", "with rollback"], repo="Roomtone", tsize=9.8)
arrow(80, 31.5, 84, 31.5)
ax.text(95, 40.9, "mic recordings in; proposals out", ha="center", va="center", fontsize=8, color=INK)
arrow(106, 31.5, 110, 31.5)
box(62, 6, 28, 14, "Test kits", ["sweep, sub, dialogue,", "reflections, drift, bar"], repo="Roomtone", tsize=9.8)
box(94, 6, 30, 14, "Status + control page", ["127.0.0.1 only; mpv overlay (C)"], repo="Roomtone", tsize=9.8)
box(128, 6, 28, 14, "Mic calibration", ["removes the mic's own", "response from every run"], repo="Roomtone", tsize=9.8)
# room.json is read by set-eq.py, which lives in linux-theater-dsp
arrow(116, 39, 104, 60, dashed=True, color=REPO["Roomtone"], label="read by set-eq.py", lx=113, ly=52.5)

# ---------------- listening tool (below the measurement band) ----------------
ax.text(2, -0.8, "LISTENING: move a test sound around the room, on demand", fontsize=9.5, fontweight="bold", color=MUTED)
group(2, -22.5, 156, 19.5, "Spatial-Lab", "3D test bench; needs none of the other repositories")
box(4, -21, 36, 13.5, "Control page", ["Three.js room, drag the object,", "paths, record and replay"], repo="Spatial-Lab", tsize=9.4)
box(44, -21, 40, 13.5, "Engine (Python)", ["VBAP panning, distance cues, delay,", "polarity, decorrelation; starts muted"], repo="Spatial-Lab", tsize=9.4)
box(88, -21, 28, 13.5, "pw-cat", ["8 channels, PipeWire"], repo="Spatial-Lab", tsize=9.4)
box(120, -21, 36, 13.5, "Output", ["Direct: the USB interface", "Through: CamillaDSP first"], ext=True, tsize=9.4)
arrow(40, -14.2, 44, -14.2)
arrow(84, -14.2, 88, -14.2)
arrow(116, -14.2, 120, -14.2)

# ---------------- sdht strip ----------------
ax.add_patch(FancyBboxPatch((2, -27.4), 156, 3.4, boxstyle="round,pad=0.0,rounding_size=0.8", linewidth=2.0,
                            edgecolor=REPO["sdht"], facecolor=REPO["sdht"] + "18"))
ax.text(4, -25.7, "sdht (this repository)", fontsize=10.5, fontweight="bold", color=REPO["sdht"], va="center")
ax.text(46, -25.7, "the front door: documentation, build log, measurement results and graphs, preflight health report, clone-all.sh",
        fontsize=8.8, color=MUTED, va="center")

for ext in ("png", "svg"):
    fig.savefig(os.path.join(OUT, f"ecosystem-map.{ext}"), facecolor=BG, bbox_inches="tight", pad_inches=0.3)
print("wrote", os.path.normpath(os.path.join(OUT, "ecosystem-map.png")))
