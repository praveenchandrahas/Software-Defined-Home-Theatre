# Packaging and installing

**Status: pre-release 0.1.0. Experimental.** Written with an AI assistant; checked against simulated rooms and REW exports; used and checked by the author in his own room (one room, one author). No external or second-person validation yet.

What the packaging adds is a way to install the project parts without copying scripts by hand. What it does **not** add is any evidence that the software works on another machine. The packaging itself has not been run on the author's rig; it was built and tested in simulation and in a clean Ubuntu 24.04 environment (a chroot while it was written, a Docker container in GitHub Actions). Try it on a spare machine or a throw-away user first.

## Which parts are packaged

| Package | From | Contains | Setup command (run as your user) |
|---|---|---|---|
| `linux-theater-dsp` | [linux-theater-dsp](https://github.com/praveenchandrahas/linux-theater-dsp) | `eq` / `theater-route`, `theater-set-eq`, `roomtone-layout`, the upmixers, the router and upmix user units | `theater-setup` |
| `roomtone` | [Roomtone](https://github.com/praveenchandrahas/Roomtone) | `autocal`, `theater-ctld` (status page, 127.0.0.1 only), the mpv status overlay, the measurement scripts | `roomtone-setup` |
| `seekthumbs` | [seekthumbs](https://github.com/praveenchandrahas/seekthumbs) | `seekthumbs`, its local web page (127.0.0.1 only), the mpv viewer script, a user unit for the watcher | `seekthumbs-setup` |
| `mpv-shelf` | [mpv-shelf](https://github.com/praveenchandrahas/mpv-shelf) | `shelf-index`, `shelf.lua` | `mpv-shelf-setup` |
| `mpv-object-audio` | [mpv-object-audio](https://github.com/praveenchandrahas/mpv-object-audio) | the wrapper and the installer script **only** | `mpv-object-audio-install` |
| `sdht` | this repository | meta package: depends on the exact versions above, `sdht-setup`, the documentation | `sdht-setup` |

All are `Architecture: all` (shell, Python and Lua; no compiled code). Files go under `/usr` only: commands in `/usr/bin`, code in `/usr/lib/<package>`, user units in `/usr/lib/systemd/user`, documentation and examples in `/usr/share/doc/<package>`.

**What the packages never do.** The maintainer scripts do nothing at install time: they do not enable or start a service, do not write into any home folder, and do not touch CamillaDSP or PipeWire configuration. The only maintainer script is a `postrm` that deletes Python byte-code that root may have written next to the installed scripts. `dpkg -r` and `dpkg --purge` leave nothing (CI asserts this). Everything per-user happens when you run the setup command, and each has `--dry-run`, `check` and `uninstall`.

**Not in any package.** CamillaDSP (not in Ubuntu's repositories; `install.sh` fetches the official release, see below) and the player stack: Omniphony, harletty-bridge and mpv-omniphony are other people's software. The `mpv-object-audio` package contains only the author's wrapper and installer; running `mpv-object-audio-install` as your user downloads their releases and builds mpv from source into `~/.local/opt/mpv-object-audio`, exactly as the installer in that repository always did. `install.sh` checks for the stack and points to [rebuild-checklist.md](rebuild-checklist.md); it never downloads it.

## Three ways to install

### 1. The installer script (recommended): download, read, verify, run

Do not pipe it from `curl` into a shell. Download it, read it (it is plain bash, about 200 lines), check it against the release checksum, then run it:

```bash
TAG=v0.1.0
curl -fLO https://github.com/praveenchandrahas/Software-Defined-Home-Theatre/releases/download/$TAG/install.sh
curl -fLO https://github.com/praveenchandrahas/Software-Defined-Home-Theatre/releases/download/$TAG/SHA256SUMS
sha256sum -c SHA256SUMS --ignore-missing          # must say: install.sh: OK
less install.sh                                    # read it
bash install.sh --dry-run                          # prints the plan; fetches only SHA256SUMS and versions.lock
bash install.sh                                    # asks before it downloads, and before it uses sudo
```

What it does: downloads `SHA256SUMS` and `versions.lock` of that one release; downloads the packages from the same release and checks **every** file against `SHA256SUMS`; shows the plan; asks; then runs **one** `sudo apt-get install -y ./*.deb` (sudo is used for nothing else, and not at all if you are root); installs CamillaDSP 4.1.3 into `~/.local/bin` after checking the SHA256 pinned in `versions.lock`; checks (never downloads) the player stack; prints the next steps. Any checksum mismatch stops it before anything is installed.

CamillaDSP: the pinned asset is `camilladsp-linux-pipewire-amd64.tar.gz` of the [official 4.1.3 release](https://github.com/HEnquist/camilladsp/releases/tag/v4.1.3) (the PipeWire build, 4.1.3 being the version the author runs). Its SHA256 `04388dfbf0999732c51a972fa7c3dc7fa17437333124af7918022445c459851a` is the digest GitHub shows for that asset; the release publishes no separate checksum file, and the same value came out when the asset was downloaded and hashed while this was written. The author's own copy is in `/usr/local/bin`; `install.sh` leaves an existing 4.1.3 alone and tells you if another `camilladsp` comes first on `PATH`.

### 2. The .deb files by hand

Download the files from the [release page](https://github.com/praveenchandrahas/Software-Defined-Home-Theatre/releases) (the main release has copies of all of them), verify, install:

```bash
sha256sum -c SHA256SUMS --ignore-missing
sudo apt install ./linux-theater-dsp_0.1.0_all.deb ./roomtone_0.1.0_all.deb ./seekthumbs_0.1.0_all.deb \
                 ./mpv-shelf_0.1.0_all.deb ./mpv-object-audio_0.1.0_all.deb ./sdht_0.1.0_all.deb
sdht-setup --dry-run install     # then without --dry-run
```

A single component works on its own, except `roomtone`, which depends on `linux-theater-dsp`.

### 3. pipx, or straight from git

```bash
pipx install git+https://github.com/praveenchandrahas/Roomtone        # autocal and autocal-web
```

This installs the `autocal` command (measurement, analysis, simulation, report) and `autocal-web` (the results page, 127.0.0.1 only). It does **not** install the status and control page, the services, the mpv overlay or `eq`: those need the `.deb` (or the repositories' own installers) because they are a router, user units and files in the mpv folders, not a Python package. `linux-theater-dsp` has no pipx entry point: its code is a folder of scripts and a router that must run as a user service, not an importable package, so a Python package would be a thin and misleading wrapper. The repositories' own installers still work as before (`git clone`, then `scripts/install-autoroute.sh`, `gui/install-ctld.sh`, `install-shelf.sh`, `seekthumbs.py install-viewer`).

Publishing to PyPI is possible later but needs an account and a token that this project does not have; nothing is published there.

## Hand-installed copies can hide the packaged ones

The older installers put commands into `~/.local/bin` and units into `~/.config/systemd/user`. On a default Ubuntu `~/.local/bin` comes **before** `/usr/bin` on `PATH`, and a unit in `~/.config/systemd/user` overrides the one in `/usr/lib/systemd/user`. So an old hand-installed `eq`, `shelf-index`, `autocal` or `theater-router.service` silently wins over the packaged one. Every `*-setup` command checks for this and says so (`theater-setup check`, `sdht-setup check`). To switch to the packaged versions, remove the old copies with the old installers' `remove` option. The setup commands never delete them for you.

## Uninstall

```bash
sdht-setup uninstall                     # stops and disables the user services, takes the mpv scripts out (your data stays)
sudo apt purge sdht linux-theater-dsp roomtone seekthumbs mpv-shelf mpv-object-audio
rm ~/.local/bin/camilladsp               # only if install.sh put it there
```

Left alone on purpose: `~/.config/roomtone/layout.yml`, `~/.config/camilladsp`, `~/.config/seekthumbs`, `~/.local/share/mpv-shelf`, `~/.local/share/roomtone/runs`, `~/.local/state/theater` and your thumbnails.

## Checking what you downloaded

Every release has a `SHA256SUMS` file: `sha256sum -c SHA256SUMS --ignore-missing`. Where the release notes say attestations were created, GitHub also holds a signed build-provenance record (keyless, from the workflow's OIDC identity) for each file:

```bash
gh attestation verify roomtone_0.1.0_all.deb --repo praveenchandrahas/Roomtone
```

This ties the file to the workflow run that built it from the tagged commit. It does not tell you the code is good. The packages are **unsigned**: there is no GPG key in this pipeline, and generating one inside a CI job would defeat its purpose. A signed apt repository would need the author's own key and hosting.

The build is reproducible: the release workflow builds every package twice (different folders, times and umask) and refuses to publish if one byte differs. You can repeat it: check out the tag and run `packaging/kit/build-deb.sh` (in the sdht repository; it takes `--repo` for any component), compare the SHA256 with the release.

## What the checks prove, and what they do not

CI proves that the packages build reproducibly from a tag, that the repositories' simulated test suites pass, that shellcheck is clean, that lintian finds no error or warning, that the package installs on a clean Ubuntu 24.04, that a smoke test run from the installed paths passes (a simulated autocal run; the status page starts and listens on 127.0.0.1 only; the setup commands in dry run), and that removing and purging leaves nothing behind. It runs without audio hardware, a PipeWire daemon or CamillaDSP. A green badge means exactly that. It does not mean the software works on a real rig; the signal-processing code has been used and checked by the author in one room and by nobody else.

## Formats that were deliberately not built

- **Flatpak.** The tools manage PipeWire links, user systemd services and CamillaDSP on the host. A sandbox would need broad host access (the PipeWire socket, `systemctl --user`, the host's files) to do that, which defeats the point of a sandbox. A component that is truly self-contained could be a Flatpak; none of these is (`seekthumbs` and `mpv-shelf` run inside the host's mpv and read the host's library).
- **AppImage.** Same reasoning: this is not one GUI application. It is user units, PipeWire graph management and CamillaDSP configuration on the host, which an AppImage cannot install. It would also have to bundle Python, numpy and scipy (large) for what a pure-Python `.deb` or pipx already gives, and still need the host's `pw-link`, `pw-cat` and `camilladsp`.
- **System image (ISO or disk image).** Not testable in this setup, huge, tied to one rig's hardware (a Z906 and a USB interface), and it would mix in other people's software and trademarks. `install.sh` plus [rebuild-checklist.md](rebuild-checklist.md) is the replacement.
- **Container image of the demo.** Skipped: a demo would need a status page reachable from outside the container, and the author's rule is no LAN listener. CI uses containers only to test, and publishes none.
- **PyPI, a PPA, Flathub, a signed apt repository.** Each needs an account or a key that belongs to the author. See "What the author has to do" in [release-process.md](release-process.md).
- **Anything with Dolby, DTS or Atmos in a package name, or a bundled decoder.** No. The names are neutral and no third-party binary is shipped.
