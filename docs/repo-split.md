# Repository split (2026-10-25, revised to five repositories 2026-10-26)

The project began as one repository holding several independent sub-projects. It was divided so that each can be used, versioned and shared on its own. The new repositories were cut from this one with `git filter-repo`, so **every file keeps its history** (commit hashes differ).
An earlier plan had seven; it was cut to five because the upmixers always run with the router and the drift tracker is a measurement tool.

## The repositories and what depends on what

| Repository | Contents (original paths) | Needs |
|---|---|---|
| `sdht` | `docs/`, `README.md`, `CHANGELOG.md`, `scripts/{preflight,check-installed.sh,collect-versions.sh,clone-all.sh,test-all.sh}`, the `tools/make-*.py` figure scripts, `docs/graphs`, `docs/img` | reads the others (figures, preflight, check) |
| `linux-theater-dsp` | `scripts/{theater-route,set-eq.py,upmix.py,upmix_engine.py,install-autoroute.sh,route-mpv.sh,make-default.sh}`, `configs/`, `tools/upmixtest/`, router, config and engine tests | nothing else (the upmixers are in the same repository) |
| `mpv-object-audio` | `scripts/object-audio-install.sh`, `mpv-object-audio`, `mpv-atmos`, `mpv-atmos-overlay-off.lua`, `docs/omniphony-debugging.md` | nothing; optionally calls `eq` from `linux-theater-dsp` |
| `seekthumbs` | `tools/seekthumbs/` (now the repo root), `docs/seekthumbs.md` (now the README), its test | nothing; works with any mpv + uosc |
| `theater-measurement` (renamed **Roomtone**, 2026-10-26; also holds the status page `gui/` and the mpv overlay `overlay/`, moved from linux-theater-dsp and mpv-object-audio) | `tools/{sweeptest,subtest,reflecttest,dialoguetest,bartest,drifttest}`, `tools/analyze-delaytest.py`, `tools/miccal.py`, `scripts/{rec.sh,tone-test.sh,make-bedtest.py,make-delaytest.py}`, `data/`, `docs/measurement.md` | nothing (the kits use each other inside the repo) |

The only cross-repository couplings are **figure scripts, `preflight` and `check-installed.sh` reading files from sibling repositories**, and the upmix test harness reading nothing outside its own repository.

## How the repositories find each other

Clone them side by side (`scripts/clone-all.sh`), keeping the folder names. `SDHT_WORKSPACE` (the parent folder) overrides the lookup for the figure scripts, `preflight`, `check-installed.sh` and `test-all.sh`.
Installed copies in `~/.local/bin` are unchanged: the router, `set-eq.py`, `upmix.py` and `upmix_engine.py` still sit side by side there.

## Checking the whole thing

`scripts/test-all.sh` runs the tests of every sibling that has some. `scripts/check-installed.sh` (read-only) compares what is installed with the repositories; `scripts/preflight` includes it.
Each repository also runs its tests on GitHub (`.github/workflows/test.yml`), with read-only permissions and no secrets.

## Known loose ends

- Prose in the documentation names files by their old path (`scripts/set-eq.py`, `tools/sweeptest/`); links were rewritten to the new repositories, plain mentions were not. The table above maps old paths to repositories.
- Code comments in the new repositories still point at `docs/runbook.md` and similar; those documents are in `sdht`.
- The sandbox that prepared the split cannot create GitHub repositories. They are published with `publish-split.sh` (in the bundle that came with this change).

## Added after the split: Spatial-Lab (2026-11-08)

Spatial-Lab, the 3D listening test bench, is the seventh repository. It was not cut from this one: it was written new as its own repository (Apache-2.0, Python, no dependency on the other six). It reads its own layout file, `spatial_lab/layouts/author-5.1.2.yml`, not Roomtone's `layout.yml`, so a layout change has to be made in both places for now. It is picked up by `scripts/clone-all.sh`, `scripts/test-all.sh` (through its `tests/run.sh`) and the repository-state list in `scripts/check-installed.sh`. It is not packaged (no `.deb`) and is not in `versions.lock`; it runs from the repository (`python3 -m spatial_lab serve`).
