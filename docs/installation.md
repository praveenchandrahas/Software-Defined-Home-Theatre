# Installation

This repository covers the audio routing, DSP and measurement parts. The player in use, `mpv-object-audio` (the Omniphony engine, harletty-bridge and an mpv built from mpv-omniphony), is installed by `scripts/object-audio-install.sh` ([below](#mpv-object-audio-the-omniphony-player-stack-2026-10-25)). The earlier hand-built player behind `mpv-atmos` is kept as a backup and is not updated (decided 2026-10-29); section 2 records both. Everything below is in use on the real system: the auto-router, profile switching and the `eq` switch have run daily since the first days of November 2026, through many reboots with the USB interface connected ([status.md](status.md)). The media library mount is not covered here.

## 1. Requirements

- Linux with **PipeWire** and WirePlumber (user services), and `pw-link`, `pw-record`, `pw-play`, `pactl`.
- **CamillaDSP 4.x** at `/usr/local/bin/camilladsp`, run as the user service `camilladsp.service` (an example unit:
  `configs/systemd/camilladsp.service.example`).
- **Python 3** with `numpy`, `scipy`, `pyyaml` (tools and tests) and `matplotlib` (diagram script only); `ffmpeg` for the bed test.
- A 7.1 USB audio interface exposed to PipeWire as an 8-channel sink.
- For measurements: a calibrated measurement microphone on a second audio device, and REW (V5.31.3 used).

Debian/Ubuntu-style packages: `pipewire-bin wireplumber pulseaudio-utils ffmpeg python3-numpy python3-scipy python3-yaml python3-matplotlib`.

## 2. Player stack

### Versions recorded on the reference laptop (2026-10-24, from `scripts/collect-versions.sh`)

The laptop, the operating system and the audio parts are what the rig runs today. The Omniphony, harletty-bridge and mpv rows are the **backup** player, `mpv-atmos`; the player in use, `mpv-object-audio`, is recorded [below](#mpv-object-audio-the-omniphony-player-stack-2026-10-25): engine v0.7.0, harletty-bridge v0.9.0, mpv v0.41.0-72-ge006f5ca0.

| Part | Version and where | Notes |
|------|-------------------|-------|
| Laptop | TIMI "Mi NoteBook Ultra", Core i5-11300H, 15.4 GB, Iris Xe | VAAPI driver iHD 24.1.0, Mesa Vulkan 25.2.8 |
| OS | Kubuntu 24.04 (Ubuntu 24.04.5 LTS), kernel 7.0.0-38-generic, KDE Plasma on Wayland | The author's everyday laptop, not a dedicated media PC |
| PipeWire | 1.0.5 (`1.0.5-1ubuntu3.3`) | clock 48 kHz only, quantum 1024 (min 32, max 2048) |
| WirePlumber | 0.4.17 (`0.4.17-1ubuntu4.1`) | |
| CamillaDSP | 4.1.3 (05e9cfc), `/usr/local/bin/camilladsp`, user service `camilladsp.service` | PipeWire capture and playback, 8 channels, chunk size 1024; config `~/.config/camilladsp/config.yml` is written by `set-eq.py` |
| Omniphony | package `omniphony-studio` 0.4.2; `liborender` 0.3.0 (bridge API 0.3.0, `abi_stable` 0.11.3) | Two copies of 10,284,384 bytes: `/usr/lib/Omniphony Studio/engine/liborender.so.0` (25 Jul) and the one mpv loads, `~/.local/share/omniphony/lib/liborender.so.0` (2 Aug). The git commit is not recoverable from the install (no checkout); the earlier note of commit 6ffaf21 is not re-verified |
| harletty-bridge | `libharletty_bridge.so`, 3,636,184 bytes (2 Aug), bridge API 0.3.0, built with rustc 1.97.1 | The library carries no version number or commit. A copy sits in `~/.local/share/omniphony/lib/` and the one mpv is told to use is next to the mpv-omniphony build |
| mpv-omniphony | mpv 0.41.0 (patched, "-dirty"), built from source on 2 Aug 2026 16:19, `~/HomeTheatre/Omniphony/mpv-omniphony-v0.4.2-linux-x86_64/mpv-omniphony/build/mpv-v0.41.0/_b/mpv` | FFmpeg 6.1.1-3ubuntu5+esm15, libplacebo 6.338.2. The system mpv (0.37.0) and a snap mpv are separate and not used by `mpv-atmos` |

Both players load their bridge: Atmos and DTS:X films play with object rendering on the rig. Still not recorded: the contents of `~/.config/omniphony/config.yaml` (23 Oct, "measured layout"). The USB interface was not plugged in during this run, so the audio-device section shows only the laptop's own outputs.

### mpv configuration

There is **no `mpv.conf`** in use. Both players get their options from their wrapper on the command line: the decoder, VAAPI, gpu-next on Vulkan, tone-mapping to 60 nits, debanding and the cache.

- **`mpv-object-audio`** (in use) runs with `--config-dir=~/.config/mpv-object-audio`, so plain mpv and `mpv-atmos` never read its settings. Its installer copied `input.conf`, `script-opts`, `scripts` and `fonts` from `~/.config/mpv` once; after that the two folders are separate. The `mpv.conf` in that folder holds only a comment. The wrapper calls `eq ensure` and `eq prepare` and opens mpv's IPC socket, so the router can pick the profile for each film.
- **`mpv-atmos`** (backup) reads `~/.config/mpv/`: `input.conf` (`o` toggles the Omniphony trajectory overlay), the `uosc` on-screen UI with its `script-opts/uosc.conf`, and `scripts/mpv-atmos-overlay-off.lua` (the repository copies are `scripts/mpv-atmos` and `scripts/mpv-atmos-overlay-off.lua`). The copy installed on the laptop is older than the repository's: it runs `eq ensure` but not `eq prepare` and opens no IPC socket, so automatic profile selection does not work from it. It is not being updated (decided 2026-10-29), since `mpv-atmos` is only the backup.

### Recorded since

- `mpv-object-audio`'s versions after its first real run on 2026-10-25, from `~/.local/opt/mpv-object-audio/VERSIONS`: engine v0.7.0 (ABI 0.12), harletty-bridge v0.9.0 (bridge API 0.6.0), Omniphony 55af2c5, mpv-omniphony b84a7c7, mpv v0.41.0-72-ge006f5ca0. `mpv-atmos` stays as the backup; it is not retired.
- The media library is a Decypharr FUSE mount; Decypharr runs in a Docker container on the laptop. Its setup is not documented here, and where the films come from is deliberately not stated (decided 2026-10-26).

## 3. Configure the interface name

The USB interface's PipeWire name is hard-coded in four places. Check it with `pw-link -i | grep usb`:

| File | Setting |
|------|---------|
| `scripts/set-eq.py` | `USB = "..."` near the bottom |
| `scripts/route-mpv.sh` | `USB=...` at the top |
| `scripts/tone-test.sh` | `USB=...` at the top |
| `scripts/theater-route` | `THEATER_USB` environment variable, default in the file |

Default: `alsa_output.usb-0d8c_USB_Sound_Device-00.analog-surround-71`.

## 4. CamillaDSP config and service

```bash
mkdir -p ~/.config/camilladsp
./scripts/set-eq.py --set=drone2 --align=bed        # writes ~/.config/camilladsp/config.yml, restarts the service
```

(Needs `camilladsp.service` to exist first: copy the example unit to `~/.config/systemd/user/`, run
`systemctl --user daemon-reload && systemctl --user enable --now camilladsp.service`.)
`configs/camilladsp/example-drone2-bed.yml` is what this generates.

## 5. Auto-routing and the `eq` command

```bash
./scripts/install-autoroute.sh
```

This copies `theater-route` to `~/.local/bin`, links `eq` to it, writes and enables
`~/.config/systemd/user/theater-router.service`, starts it, makes sure `camilladsp.service` is enabled, and prints
`eq status`. It reports the lingering state: if the machine does not auto-login to the desktop, run
`loginctl enable-linger $USER` once so user services start at boot. Remove everything with `./scripts/install-autoroute.sh remove`.

## 6. Check it

```bash
tests/run.sh          # no hardware needed
eq status             # with a film playing
```

Then follow the reboot test in [runbook.md](runbook.md).

## mpv-object-audio: the Omniphony player stack (2026-10-25)

`scripts/object-audio-install.sh` installs the latest engine and bridges as **prebuilt releases** (`liborender-<tag>-linux-x86_64.zip` from mgth/Omniphony, `harletty-bridge-<tag>-linux-x86_64.zip` from harletty/harletty-bridge) and builds **only mpv-omniphony from source**, because it publishes no releases (main of mgth/mpv-omniphony, which pins the mpv fork tag: mpv 0.41.x plus the `ad_orender` patches; the build needs no engine). Everything goes into `~/.local/opt/mpv-object-audio`, and the installer refuses to install the command unless the new mpv loads the engine. It is **independent of `mpv-atmos`**: separate mpv binary, engine and bridges, and its own mpv config folder `~/.config/mpv-object-audio` (a one-time copy of `~/.config/mpv`: keys, uosc, the overlay script). The wrapper `scripts/mpv-object-audio` carries the same video settings as `mpv-atmos` (VAAPI, gpu-next on Vulkan, BT.709/BT.1886, peak 60, bt.2390, mitchell with linear downscaling, debanding, 512 MiB demuxer cache).

```bash
scripts/object-audio-install.sh deps      # prints the apt line (mpv's build dependencies)
scripts/object-audio-install.sh           # install or update (a re-run takes the latest releases)
scripts/object-audio-install.sh status
scripts/object-audio-install.sh remove
```

Entry points: `mpv-object-audio FILE` in a terminal; Dolphin right-click submenu "mpv-object-audio" (play, fullscreen, play with log in Konsole, show streams); "Open with" in any KDE file dialog. It is not made the default handler. The DSP hooks (`eq ensure`, `eq prepare`) and the IPC socket are shared with `mpv-atmos` on purpose, so the router and the automatic profile switching work unchanged; `OBJECT_AUDIO_DSP=0` turns them off. The bridge pairing: the latest engine and the latest bridge release should match (the bridge notes say which Omniphony they require); pin with `OA_OMNIPHONY_TAG` / `OA_BRIDGE_TAG` if they do not.

**Run on the rig 2026-10-25** (laptop away from the DAC): the asset names matched, the build finished, the engine (v0.7.0, ABI 0.12) and the three bridges (v0.9.0, bridge_api 0.6.0, Omniphony 55af2c5) loaded, and an Atmos TrueHD clip and a DTS:X clip played with sound. Since then `mpv-object-audio` has been the player in daily use with the DAC, routed through CamillaDSP by the router (owner, by 2026-11-08). Not recorded: the level comparison against `mpv-atmos` (`preflight compare FILE`: the new engine logs a -8 dB dialogue normalisation on the Atmos clip). The engine config `~/.config/omniphony/config.yaml` is shared with `mpv-atmos`, so layout and render settings are common to both players. The installed router was updated the same day with `install-autoroute.sh` (it was older than the repository's and lacked `eq prepare`). The download step needs GitHub's API, which a rate limit can refuse: set `GITHUB_TOKEN`.
