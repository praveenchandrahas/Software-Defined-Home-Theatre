# Releases

Release history of the install packages and the one-script installer. The day-by-day build log is CHANGELOG.md; this file is what the release workflow reads.

## [0.2.0] - 2026-11-27

Second packaged pre-release. Experimental. Only seekthumbs changes; the other four components stay at 0.1.0.

- seekthumbs 0.2.0: thumbnails for streamed films, built while the film plays and dropped when mpv closes (`seekthumbs install-viewer --live`, or `seekthumbs-setup install --live`); reading over HTTP with the keyframe flush; Real-Debrid as a source; the calibrated path for films with no seek index. The package now installs `realdebrid.py`, which 0.1.0 left out (so `source = rd` failed in a packaged install). Stream thumbnails were confirmed on the author's rig in one session; see the seekthumbs changelog for what is untested.
- New how-to: [Stremio streams in mpv-object-audio](docs/stremio-handoff.md).
- `versions.lock` pins seekthumbs 0.2.0 by the sha256 of its released `.deb`, checked against that release's own SHA256SUMS. linux-theater-dsp, Roomtone, mpv-shelf, mpv-object-audio and CamillaDSP are unchanged.

## [0.1.0] - 2026-11-01

First packaged pre-release. Experimental. It installs what was on main in each repository on 2026-11-01.

- `install.sh`: downloads the .deb packages of this release and checks them against SHA256SUMS before using sudo (for apt only), installs CamillaDSP 4.1.3 from its official release after checking its SHA256 against the pinned value, and checks, but does not download, the player stack (Omniphony, harletty-bridge, mpv-omniphony). `--dry-run` shows the plan.
- Debian meta package `sdht` (Architecture: all) that depends on the exact component versions in versions.lock: linux-theater-dsp, roomtone, seekthumbs, mpv-shelf and mpv-object-audio.
- `sdht-setup` runs the per-user setup commands of the components (`theater-setup`, `roomtone-setup`, `seekthumbs-setup`, `mpv-shelf-setup`) with `--dry-run`, `uninstall` and `check`.
- Packages are unsigned. Checksums are in SHA256SUMS; build-provenance attestations are attached when the workflow could create them.
