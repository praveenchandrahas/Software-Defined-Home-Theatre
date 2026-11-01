# Releases

Release history of the install packages and the one-script installer. The day-by-day build log is CHANGELOG.md; this file is what the release workflow reads.

## [0.1.0] - 2026-11-01

First packaged pre-release. Experimental. It installs what was on main in each repository on 2026-11-01.

- `install.sh`: downloads the .deb packages of this release and checks them against SHA256SUMS before using sudo (for apt only), installs CamillaDSP 4.1.3 from its official release after checking its SHA256 against the pinned value, and checks, but does not download, the player stack (Omniphony, harletty-bridge, mpv-omniphony). `--dry-run` shows the plan.
- Debian meta package `sdht` (Architecture: all) that depends on the exact component versions in versions.lock: linux-theater-dsp, roomtone, seekthumbs, mpv-shelf and mpv-object-audio.
- `sdht-setup` runs the per-user setup commands of the components (`theater-setup`, `roomtone-setup`, `seekthumbs-setup`, `mpv-shelf-setup`) with `--dry-run`, `uninstall` and `check`.
- Packages are unsigned. Checksums are in SHA256SUMS; build-provenance attestations are attached when the workflow could create them.
