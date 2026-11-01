# Rebuild checklist

A short ordered list for rebuilding the rig on a new laptop or the planned desktop, starting from a clean Ubuntu 24.04.
It is a checklist, not an installer. It links to the existing documents instead of repeating them.
Written 2026-10-31. Nothing here was run end to end on a clean machine; the order is taken from the documents.

**Two player stacks exist on the laptop.** Do not mix them up.

- **Current player:** `mpv-object-audio`, installed by `object-audio-install.sh` (Omniphony engine v0.7.0, harletty-bridge v0.9.0). This is the one in use. See [installation.md](installation.md#mpv-object-audio-the-omniphony-player-stack-2026-10-25).
- **Backup player:** `mpv-atmos`, hand-installed (omniphony-studio 0.4.2, liborender 0.3.0, bridge API 0.3.0, patched mpv 0.41.0 built on 2 Aug 2026). It is only a backup and is not updated (decided 2026-10-29). Step 8 covers it.

The versions in the [version table](installation.md#2-player-stack) (dated 2026-10-24) describe the backup player. Pins for both are in the [pins section](#pins-for-omniphony-and-harletty-bridge).

Repositories used: `sdht` (this one), `linux-theater-dsp`, `mpv-object-audio`, `seekthumbs`, `mpv-shelf`, `Roomtone`. `scripts/clone-all.sh` clones them side by side into `~/sdht-workspace`.
`docs/omniphony-debugging.md` and `scripts/mpv-atmos` live in the `mpv-object-audio` repository, not in this one ([repo-split.md](repo-split.md)).

## Before you start: copy these off the old machine

None of them can be regenerated from the repositories. The list is the one in [runbook.md](runbook.md#backups).

- [ ] `~/.config/omniphony/` (`config.yaml`, `overlay-prefs.conf`). The contents of `config.yaml` are still not recorded in the docs.
- [ ] `~/.config/mpv/` (`input.conf`, `script-opts`, `scripts`) and `~/.config/mpv-object-audio/`
- [ ] `~/.local/bin/mpv-atmos` (the hand-installed backup wrapper)
- [ ] `~/.config/camilladsp/config.yml` (regenerable with `set-eq.py`, but keep it)
- [ ] `~/.config/seekthumbs/config.ini` (TMDB key, `read_url_base`) and the thumbnail store, if you want to keep the built thumbnails
- [ ] `~/.config/pipewire/` and `~/.config/wireplumber/` (see step 2: the repository does not record the 48 kHz setting)
- [ ] The microphone calibration file (also in the Roomtone repository, `data/mic/`)
- [ ] Decypharr's own settings (not in any repository)
- [ ] Output of `scripts/capture-pins.sh` (see [pins](#pins-recorded-on-the-rig)), if it was not run yet

## 1. OS and kernel

- [ ] Install Ubuntu 24.04 LTS (Kubuntu, KDE on Wayland on the laptop). Reference: Ubuntu 24.04.5, kernel `7.0.0-38-generic`.
- [ ] Record `uname -r`. Whether the kernel version matters beyond "Intel graphics and the USB audio interface work" is not known.
- [ ] Packages: `pipewire-bin wireplumber pulseaudio-utils ffmpeg python3-numpy python3-scipy python3-yaml python3-matplotlib` ([installation.md](installation.md#1-requirements)).
- [ ] Video: VAAPI driver (`iHD` 24.1.0 on the laptop) and Mesa Vulkan (25.2.8). `vainfo` must list HEVC and H.264. A desktop with a different GPU needs its own check.

## 2. PipeWire and WirePlumber (48 kHz lock)

- [ ] PipeWire 1.0.5 and WirePlumber 0.4.17 are what Ubuntu 24.04 ships. The rig runs them as shipped.
- [ ] The clock must be locked to 48 kHz only, quantum 1024 (min 32, max 2048). Check: `pw-metadata -n settings`.
- [ ] **The file that sets this is not recorded in the repository.** Copy it from the old machine (`~/.config/pipewire/`). If it is lost, a standard drop-in is `~/.config/pipewire/pipewire.conf.d/` with `default.clock.rate = 48000`, `default.clock.allowed-rates = [ 48000 ]`, `default.clock.quantum = 1024`, `default.clock.min-quantum = 32`, `default.clock.max-quantum = 2048`. That is the generic PipeWire form, not a copy of the rig's file. Compare it with `pw-metadata` output from the old machine.
- [ ] Restart: `systemctl --user restart pipewire wireplumber`.

## 3. CamillaDSP 4.1.3 and its user service

- [ ] Download CamillaDSP **4.1.3** from the [releases page](https://github.com/HEnquist/camilladsp/releases) and install it as `/usr/local/bin/camilladsp`. The recorded build is `05e9cfc`. Check: `camilladsp --version`.
- [ ] Install the user unit from `linux-theater-dsp/configs/systemd/camilladsp.service.example` into `~/.config/systemd/user/`. The rig's `ExecStart` is `/usr/local/bin/camilladsp %h/.config/camilladsp/config.yml`, plus the websocket flags `-p <port> -a 127.0.0.1` (loopback only, used by theater-ctld). The example unit has not been compared with the installed one (open item in [todo-fill-in.md](todo-fill-in.md)). Compare with `systemctl --user cat camilladsp.service` on the old machine.
- [ ] `systemctl --user daemon-reload && systemctl --user enable --now camilladsp.service`
- [ ] Config: PipeWire capture and playback, 8 channels, chunk size 1024, written by `set-eq.py` (step 7).

## 4. Omniphony and harletty-bridge, and the current player

- [ ] `cd ~/sdht-workspace/mpv-object-audio && ./scripts/object-audio-install.sh deps` and run the `apt` line it prints.
- [ ] Set `GITHUB_TOKEN` if GitHub's API rate limit refuses the download.
- [ ] To get the same versions as the rig and not "latest", set `OA_OMNIPHONY_TAG` and `OA_BRIDGE_TAG` before running the installer (see [pins](#pins-for-omniphony-and-harletty-bridge)). The engine and the bridge must agree on the `bridge_api` minor version.
- [ ] `./scripts/object-audio-install.sh` (builds only mpv-omniphony from source, several minutes). It refuses to install the command unless the new mpv loads the engine.
- [ ] `./scripts/object-audio-install.sh status`, then read `~/.local/opt/mpv-object-audio/VERSIONS` and add it to the [pins block](#pins-recorded-on-the-rig).
- [ ] Restore `~/.config/omniphony/` from the backup (engine config, shared by both players).
- [ ] Check which bridge the engine uses: `mpv-object-audio --oa-check`. The shared config points at `~/HomeTheatre/Omniphony/libharletty_bridge.so`, which on the old machine is byte-identical to the backup player's bridge (v0.7.3), not to the current player's v0.9.0.

## 5. mpv config folder and wrapper

- [ ] The installer makes `~/.config/mpv-object-audio` as a one-time copy of `~/.config/mpv`. Restore `~/.config/mpv/` from the backup **before** running the installer, so the copy is the right one.
- [ ] There is no `mpv.conf`. The video settings are in the wrapper (`mpv-object-audio`). `~/.config/mpv/` holds `input.conf` (`o` toggles the trajectory overlay), the `uosc` UI with `script-opts/uosc.conf`, and `scripts/mpv-atmos-overlay-off.lua`.
- [ ] Install `uosc` into the mpv config folder.

## 6. Media mount (Decypharr, FUSE)

- [ ] Install Decypharr and mount the library with FUSE. How much of this to document is the author's choice ([installation.md](installation.md#still-todoowner)), so the settings are not in the repositories. Restore them from your own backup.
- [ ] Check `ls` on the mount and a short read of one film before moving on. Slow first reads on the mount are known ([todo-fill-in.md](todo-fill-in.md)).

## 7. Audio hardware, routing, DSP and control

- [ ] Plug in the Vantec 7.1 USB interface. Check its name: `pw-link -i | grep usb`. Default: `alsa_output.usb-0d8c_USB_Sound_Device-00.analog-surround-71`. If it differs, change it in the four places listed in [installation.md](installation.md#3-configure-the-interface-name).
- [ ] **Z906 levels:** sub level and master volume are **both exactly 50 % on the knob** ([runbook.md](runbook.md#z906-rules)). The tuning assumes the sub level as it is. Do not change the sub level without re-measuring.
- [ ] `cd ~/sdht-workspace/linux-theater-dsp && ./scripts/make-default.sh`. It writes and loads the standing profile (`drone2`, `--align`, `--heights`, `--heights-tone`), installs the router and the `eq` command, and enables `camilladsp.service` and `theater-router.service`. `./scripts/make-default.sh --check` only reports.
- [ ] If the machine does not log in to the desktop by itself: `loginctl enable-linger $USER`.
- [ ] **theater-ctld** (status page and the CamillaDSP link): `cd ~/sdht-workspace/Roomtone/gui && ./install-ctld.sh`, then `systemctl --user enable --now theater-ctld.service`. It listens on `127.0.0.1:8765` only. No LAN listener (decided 2026-10-29). Overlay (key `C`): `cd ~/sdht-workspace/Roomtone/overlay && ./install-theater-status.sh --bindings`.
- [ ] **Roomtone** (the room is not the same on a new machine in a new place, but the tools are): `cd ~/sdht-workspace/Roomtone`, then `python3 -m autocal check` (plays quiet sounds, changes nothing). The delays, trims and EQ in `room.json` are for the author's room and seat only.

## 8. Backup player: the `mpv-atmos` wrapper (optional)

This is only needed if the backup player is wanted. It is not updated and is not part of the current setup.

- [ ] Copy the author's own backup of `~/.local/bin/mpv-atmos` back to the same place and `chmod +x` it. The repository copy is not the same file and is not to be copied over it.
- [ ] The wrapper expects the old build at `~/HomeTheatre/Omniphony/mpv-omniphony-v0.4.2-linux-x86_64/` (patched mpv at `.../mpv-omniphony/build/mpv-v0.41.0/_b/mpv`) and `liborender.so.0` in `~/.local/share/omniphony/lib/`. Rebuilding that tree is described in `docs/omniphony-debugging.md` (entry 1): build mpv from source, because the prebuilt Linux binary had no audio or video backends. There is no script for it.
- [ ] The pins for that tree are below. Do not take newer ones for the backup; the point of the backup is that it stays as it was.

## 9. seekthumbs and mpv-shelf

- [ ] `cd ~/sdht-workspace/seekthumbs && ./seekthumbs.py probe`, set the library and store paths in `~/.config/seekthumbs/config.ini`.
- [ ] `./seekthumbs.py install-viewer`. **It copies the Lua file** (`thumbfast.lua`) into the mpv config folder. It is not a link. **Re-run it after every `git pull`**, or mpv keeps the old copy. `scripts/check-installed.sh` shows when the copy is out of date.
- [ ] `cd ~/sdht-workspace/mpv-shelf && ./install-shelf.sh`. Put the TMDB key under `[shelf]` in `config.ini`, then run `shelf-index scan`. The installer copies its script too, so re-run it after a pull as well.

## 10. Verify

Run these in order. All of them are read-only unless noted.

- [ ] `~/sdht-workspace/sdht/scripts/check-installed.sh --diff`: installed scripts against the repositories. Exit 0 means identical. It prints the update command for anything that differs; it changes nothing.
- [ ] `~/sdht-workspace/sdht/scripts/preflight`: the health report.
- [ ] `~/sdht-workspace/sdht/scripts/collect-versions.sh --redact`: versions and configuration, to compare with the [version table](installation.md#2-player-stack). Run it with the Vantec connected and a film playing, which is still an open item.
- [ ] `scripts/capture-pins.sh`: compare its hashes with the [recorded pins](#pins-recorded-on-the-rig). A different hash for the same tag is not a fault by itself (see the notes there).
- [ ] `tests/run.sh` in `linux-theater-dsp` (no hardware needed).
- [ ] Play an Atmos film with `mpv-object-audio`. In a second terminal: `eq status` must say audio goes through CamillaDSP; then `scripts/preflight playing`.
- [ ] Reboot test ([runbook.md](runbook.md#after-a-reboot)): start a film, run `eq status`.
- [ ] Check the knobs: Z906 sub level and master volume at 50 %.

## Pins for Omniphony and harletty-bridge

Research done 2026-10-31 from the public release pages of `mgth/Omniphony` and `harletty/harletty-bridge`. **The installed copies are not git checkouts. The exact upstream commit cannot be recovered from the rig, and none is claimed here.** The short commit ids below are the ones the release pages show for each tag, not ones taken from the rig.
The release pages show day and month only, with no year (the page footer says 2026). Release asset **sizes were not visible** on the pages, so no file size could be matched to a download.

### Omniphony (engine, `liborender`, Studio)

**Best match: tag `v0.4.2`** of `mgth/Omniphony`, published 24 Jul, release page shows commit `6ffaf21`. Confidence: **sure** that the library is the one shipped in the `omniphony-studio` 0.4.2 package (`dpkg -V omniphony-studio` printed nothing on 2026-11-01, so no packaged file was changed, and the `~/.local` copy has the same hash). Not compared with the GitHub release asset, and no commit is recoverable.

Evidence for:

- The package on the rig is `omniphony-studio` **0.4.2**, and the Studio copy of `liborender.so.0` is dated 25 Jul, one day after the tag.
- The matching player release `mpv-v0.4.2` (25 Jul 00:21, also commit `6ffaf21`) pins mpv `v0.41.0` plus the repository's `patches/` at commit `2553c6d66c0be57de7b8eeee140f86a82bcdbacc`, with liborender built at Omniphony `v0.4.2`. The wrapper path on the rig is `mpv-omniphony-v0.4.2-linux-x86_64`, and mpv is 0.41.0.
- `installation.md` already carried an unverified note of commit `6ffaf21`. The release page now agrees with it.
- The two `liborender.so.0` copies on the rig have **the same sha256** (`19643d7dc481c09bada247ba2734dc5e48a8358a32619657606e7756b14667a2`, 10,284,384 bytes). One is inside the installed `omniphony-studio` 0.4.2 package (25 Jul 05:15). The other, in `~/.local/share/omniphony/lib/`, is dated 2 Aug, which is the date of the copy. So the library mpv loads is the package's file, not a separate source build (the first version of this section guessed otherwise).
- The debugging log says bridge API 0.3.x pairs with Omniphony 0.5.x and earlier, and the `v0.6.0` notes say the API moved from 0.3 to 0.4. That fits a 0.4.2 engine with bridge API 0.3.0.

Evidence against, or gaps:

- **"liborender 0.3.0" does not appear on any release page.** The standalone `liborender-*` tags seen are `v0.4.1`, `v0.4.2` (tagged, no release) and `v0.4.3`. So the "0.3.0" string is probably an internal crate or ABI version inside the `v0.4.2` build, but that is a guess.
- `v0.4.3`'s release notes and the pages for the 0.3.x tags were not fully read (`/tags` is blocked to automated readers).

For the current player: the installer records engine **v0.7.0** (ABI 0.12) and Omniphony commit `55af2c5` in `~/.local/opt/mpv-object-audio/VERSIONS`. That is the author's own record from 2026-10-25. It was not checked upstream here.

**Commands to confirm.** First, that the installed library is exactly what the package shipped (read-only; no output means no file of the package was changed; **done 2026-11-01, no output**):

```bash
dpkg -V omniphony-studio
```

Then, to compare with the release itself (lists the assets and their sizes for the tag; unpack the Linux one and look for a `liborender.so.0` with the hash above). This was not done here, because the release API was not reachable from the session that wrote this:

```bash
curl -s https://api.github.com/repos/mgth/Omniphony/releases/tags/v0.4.2 | python3 -c 'import json,sys; [print(a["size"], a["name"]) for a in json.load(sys.stdin)["assets"]]'
```

### harletty-bridge

**Match: tag `v0.7.3`** of `harletty/harletty-bridge`, published 29 Jul, release page shows commit `ff98334`. Confidence: **firm for the release, not for the commit**.

Evidence (checked 2026-11-01 after the author ran `capture-pins.sh`):

- The installed `libharletty_bridge.so` is 3,636,184 bytes with sha256 `764869132c65829fd146504c8c8f14e4e5cbe959a91656ea9ac11934c949022e`.
- The `libharletty_bridge.so` inside the release asset `harletty-bridge-v0.7.3-linux-x86_64.zip` has **the same size and the same sha256**. Both were compared byte for byte by hash.
- The `v0.7.2` asset does not match: its library is 3,546,128 bytes (sha256 `6a852128...2786f33`). So `v0.7.2`, which the first version of this section preferred, is ruled out.
- The library carries `bridge_api;0.3.0`, `abi_stable;0.11.3` and `rustc version 1.97.1 (8bab26f4f 2026-07-14)`, as expected for a 0.7.x bridge.
- The file date on the rig, 29 Jul 17:53, is the day `v0.7.3` was published. The "2 Aug" date in the version table is the date of a later copy into `~/.local/share/omniphony/lib/`. All three copies on the rig (next to the mpv build, in `~/.local/share/omniphony/lib/`, and the one the engine config points at) have the same hash.

What this does not show: the exact commit. A release zip is built by upstream's CI, so the hash proves the author installed that release's file. It does not give a commit beyond what the release page shows (`ff98334`), and that id was read from the page, not from the file. The release asset list on the pages did not show sizes; the match above comes from downloading the zip, not from the page.

To repeat the check yourself (read-only; downloads the zip into a temporary folder, prints size and hash of the library):

```bash
d=$(mktemp -d) && curl -sSL -o "$d/b.zip" https://github.com/harletty/harletty-bridge/releases/download/v0.7.3/harletty-bridge-v0.7.3-linux-x86_64.zip && unzip -q "$d/b.zip" -d "$d" && sha256sum "$d"/libharletty_bridge.so
```

The result must be `764869132c65829fd146504c8c8f14e4e5cbe959a91656ea9ac11934c949022e`.

For the backup player, install that zip's library, not a newer one. For the current player: bridges **v0.9.0**, recorded by the installer on 2026-10-25 (`VERSIONS` file below). Not compared with the release asset.

### mpv-omniphony

**Pin: release `mpv-v0.4.2`** of `mgth/Omniphony` (mpv `v0.41.0` plus `patches/` at `2553c6d66c0be57de7b8eeee140f86a82bcdbacc`). Confidence: **fairly sure**; the directory name on the rig says `v0.4.2` and the log says 24 patches (the release page gives no patch count). The binary was built on the rig on 2 Aug 2026 16:19, reports `mpv v0.41.0-dirty`, so it is not a byte-identical rebuild of anything upstream.

## Pins recorded on the rig

Run once on the laptop, with no film playing:

```bash
~/sdht-workspace/sdht/scripts/capture-pins.sh
```

It is read-only: it writes nothing, opens no listener and uses no network. Paste its output between the lines below. Done on 2026-11-01.

<!-- PINS-BEGIN -->
Captured 2026-11-01 on the laptop with `scripts/capture-pins.sh`. Kernel 7.0.0-38-generic, Ubuntu 24.04.5 LTS.

| Part | Version | Size (bytes) | File date | sha256 |
|------|---------|--------------|-----------|--------|
| PipeWire | 1.0.5 | | | |
| WirePlumber | 0.4.17 | | | |
| CamillaDSP `/usr/local/bin/camilladsp` | 4.1.3 (05e9cfc) | 8,219,840 | 2026-07-23 | `933502e484f4696a218a0a935d8fa240ba0045e2a4af929fc920d54195180081` |
| `liborender.so.0` (mpv loads, `~/.local/share/omniphony/lib/`) | bridge_api 0.3.0, abi_stable 0.11.3, rustc 1.97.1 | 10,284,384 | 2026-08-02 | `19643d7dc481c09bada247ba2734dc5e48a8358a32619657606e7756b14667a2` |
| `liborender.so.0` (in the `omniphony-studio` 0.4.2 package) | same | 10,284,384 | 2026-07-25 | same hash as above |
| `libharletty_bridge.so` (three identical copies) | bridge_api 0.3.0 | 3,636,184 | 2026-07-29 (copy 2026-08-02) | `764869132c65829fd146504c8c8f14e4e5cbe959a91656ea9ac11934c949022e` |
| mpv binary `.../mpv-omniphony/build/mpv-v0.41.0/_b/mpv` | v0.41.0-dirty | 11,739,304 | 2026-08-02 16:19 | `19b96a9f9b1c1e7bccb10bff9631e5aa6024dd00942eadee65bc6861ac1ba1a6` |
| `~/.local/bin/mpv-atmos` (backup wrapper) | | 1,611 | 2026-10-26 | `e2237e1b86bab1e77fb03e55f360f6baca17761cabfbd4256a908bcba23dee6a` |

`mpv-atmos` passes `--ad-orender-library=~/.local/share/omniphony/lib/liborender.so.0` and `--ad-orender-bridge-path=$OMNI/libharletty_bridge.so` (the copy next to the mpv build).

Current player, from `~/.local/opt/mpv-object-audio/VERSIONS` (installed 2026-10-25): engine v0.7.0, bridge v0.9.0, mpv-omniphony commit `b84a7c7d3b14f24206d6c14bbab318937dd8a5bd`, mpv `v0.41.0-72-ge006f5ca0`.
<!-- PINS-END -->

Notes for reading the result:

- A hash only identifies a file. It cannot say which commit built it.
- The mpv binary was built on the rig. A rebuild will not give the same hash.
- The CamillaDSP hash was not compared with the 4.1.3 release asset. The version string and build id `05e9cfc` are the evidence for now.
- The three bridge copies and the two liborender copies are identical, so the "which bridge does the engine use" question in the todo list does not change what is loaded: they are the same file.
