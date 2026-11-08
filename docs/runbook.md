# Runbook: using and looking after the system

## Everyday

| I want to... | Do this |
|--------------|---------|
| Watch something | Start mpv or `mpv-atmos`. Nothing else. |
| Hear it without any DSP | `eq off` (all EQ, delays and trims bypassed). `eq on` to come back. |
| See what is happening | `eq status` |
| Change the preset | `./scripts/set-eq.py --set=drone2 --align=bed` (see list below) |
| Look at the router's log | `journalctl --user -u theater-router -f` |
| Look at CamillaDSP's log | `journalctl --user -u camilladsp -n 50 --no-pager` |

`eq status` prints the switch state, whether the router and CamillaDSP services are active, which preset is on
disk, and per-channel routing counts. "audio goes through CamillaDSP (EQ active)" is the healthy line while a film plays.

A brief burst of `PipeWire playback: buffer empty, outputting silence` warnings in the CamillaDSP log when a stream
starts or stops is normal. A continuous stream of them is not (see [troubleshooting.md](troubleshooting.md)).

### Remember when comparing EQ on and off

EQ on is quieter, mostly in the bass (every filter is a cut and the trims are negative). Louder sounds better, so
raise the Z906 knob slightly with EQ on before judging, or judge at matched level.

## Standing profile

`./set-eq.py` (no arguments) applies the standing profile: `--set=drone2 --align --heights --heights-tone`. `scripts/make-default.sh` applies it, enables
`camilladsp.service` and `theater-router.service`, and makes `mpv-atmos` call `eq ensure`; `./make-default.sh --check` only reports.

## Presets

`./scripts/set-eq.py [<scale> <max_freq_hz>] [--set=NAME] [--skip=a,b] [--align|--align=bed] [--invert=FC,...] [--dry]`

| Set | What it is |
|-----|------------|
| `drone2` | **In daily use.** `punch20x` plus cuts at 72 Hz (-6 dB, Q 8) and 84 Hz (-6 dB, Q 4). |
| `drone1`, `drone3` | Gentler / stronger versions of the same idea. |
| `punch20x`, `thump20x`, `tight20x`, `punch20`, `thump20` | Bass-forward sets 20 dB above the mids with different weight at 47 / 61 Hz (history in [tuning-log.md](tuning-log.md)). |
| `hump8`, `hump14`, `hump20`, `thump14` | Earlier fits at 8 / 14 / 20 dB above the mids. |
| `rew` | The flat-target REW fit. Too lean for this room and taste. |

`--align=bed` adds the per-speaker delays and trims for FL FR FC LFE SL SR and leaves the heights alone.
`--invert=FC` flips a speaker's polarity (not needed: pair tests showed all speakers in phase).
Each run validates the config first, then restarts CamillaDSP and relinks. If anything fails, the router falls back to the direct route.

## Upmix presets (stereo and 5.1 to 5.1.2)

`./scripts/set-eq.py --upmix=stereo[:voice|balanced|wide]` or `--upmix=bed[:subtle|balanced|wide]` gives the standing profile plus the upmix
(no other flags needed). `./scripts/set-eq.py --default` goes back to film mode. Each switch restarts CamillaDSP, so do it between films, and
return to `--default` before an Atmos film (mpv's own 5.1.2 output must not pass through an upmix).

| Job | For | What it does |
|-----|-----|--------------|
| `stereo` | YouTube in Chrome, any 2.0 source | Part of the phantom centre (above 150 Hz) goes to the real centre speaker; surrounds from the side signal (200 Hz-9 kHz, decorrelated, Haas delay 12-17 ms); heights from the side signal (above 300 Hz, decorrelated, 20-25 ms). Mono speech gives nothing to the rear or the ceiling. LFE stays empty (the Z906 takes the bass). |
| `bed` | 5.1 films without Atmos (DTS-HD MA, TrueHD, FLAC) | Heights are decorrelated, delayed ambience from SL/SR plus some front side signal. Dialogue (FC) never goes up. |

Flavours: `voice` (talking heads, conservative), `balanced` (default), `wide` (music, ambience; the most centre-less and the most height). The upmix sits
in the same CamillaDSP config, so FL/FR/FC get no extra delay (checked: same impulse sample index) and lip-sync is unchanged.
Limits: it is a fixed matrix. It cannot steer a moving source, a hard-panned instrument leaks into the centre/surrounds at a reduced level, and uncorrelated
L/R become somewhat anti-correlated at the fronts (about -0.4 balanced). Pick the flavour by ear. Offline checks: `tools/upmixtest/`.
### Automatic profile (the default)

The router daemon picks the profile from what is playing; nothing to type. `eq mode auto` is the default.

| Playing | Profile | What the router does |
|---------|---------|----------------------|
| Chrome (any PipeWire node whose name matches `THEATER_STEREO_APPS`, default `chrom`) | `stereo` | Switches CamillaDSP to the stereo upmix, links Chrome's FL/FR to CamillaDSP inputs 1-2 (make before break) and drops its direct links. |
| mpv, Atmos track (codec profile contains "Atmos") | `film` | No upmix; Omniphony's own 5.1.2 render goes through as before. |
| mpv, 6-channel track | `bed` | 5.1 -> 5.1.2 bed upmix. |
| mpv, 1-2 channel track | `stereo` | Stereo upmix. |
| mpv, anything else (7.1, unknown) | `film` | No upmix. |
| nothing for `THEATER_IDLE_RESET` (120 s) | `film` | Next film starts clean. A paused video does not flip the profile. |

mpv wins when both play, so a Chrome ping (WhatsApp, say) during a film changes nothing and goes to the default sink untouched. Chrome must keep playing for `THEATER_APP_GRACE` (4 s) before it counts, so a ping with nothing else playing does not restart CamillaDSP. The source is read from mpv's IPC socket (`current-tracks/audio`: codec profile and channel count), so mpv needs
`input-ipc-server`; `mpv-atmos` passes it and also runs `eq prepare FILE` before starting mpv, so the right profile is already active and nothing switches
mid-film. For plain `mpv`, put `input-ipc-server=/run/user/1000/theater-mpv.sock` in `~/.config/mpv/mpv.conf` (use your own UID).
If mpv does not report a track within 8 s the router assumes `film`. A switch restarts CamillaDSP (about a second of silence) and is rate-limited to one per 8 s.

### Adaptive stereo upmix (the engine)

For stereo sources the upmix is adaptive by default (`eq engine on`): `scripts/upmix_engine.py` runs as `theater-upmix.service`, started and stopped by
the router while the `stereo-ad` profile is active (not enabled at boot). It reads the app's FL/FR through a PipeWire stream (`theater-upmix-in`), separates
direct sound from ambience per time-frequency tile and sends only the ambience (`theater-upmix-out`, AUX0-3) into CamillaDSP's surrounds and heights, where the
usual high-pass, decorrelation, delays, bass management and EQ apply. The fronts and the centre do not go through it (zero added latency, lip-sync unchanged);
the engine adds about 21 ms plus buffers to the rear/ceiling feeds only, which the Haas delays account for.
Measured offline (tools/upmixtest/README.md): a panned instrument leaks about 20 dB less into the rear than with the fixed matrix on realistic (harmonic) material;
on noise-like sources it is no better. Cost: about 4 % of one core. If the engine does not come up within 12 s the router falls back to the fixed matrix by itself
and says so in its log; `eq engine on` retries, `eq engine off` forces the fixed matrix. Needs numpy and scipy (the installer says if they are missing).
The engine asks for real-time priority directly, then through rtkit, and logs which it got (`journalctl --user -u theater-upmix | head`), plus a line if hops run slow. Check `pw-top` (ERR column) for xruns. Re-run `scripts/install-autoroute.sh` after pulling: it now installs `set-eq.py`, `upmix.py` and `upmix_engine.py` next to `theater-route`.

Commands: `eq mode auto|film|stereo|bed` (fixed override until `auto`), `eq flavour stereo|bed NAME`, `eq engine on|off`, `eq source` (what mpv reports and how it is classified;
paste it if detection looks wrong), `eq status` (profile, Chrome patch state, source). With `eq off` nothing is switched or patched.
Chrome's PipeWire node name and automatic profile switching have been in daily use on the real system (owner, 2026-11-08; dates not recorded). Not separately confirmed: whether WirePlumber leaves a re-linked Chrome stream alone when a film starts over it.

## Z906 rules

- **Do not change the sub level** without re-measuring the Z906 channels: all bass tuning assumes the sub as it is.
- The master volume can be changed freely: it scales all channels equally.
- Record the knob positions here: the Z906 sub level and the master volume are both at exactly 50 % on the knob (owner, 2026-10-29).

## Starting, stopping, services

```bash
systemctl --user status camilladsp.service theater-router.service
systemctl --user restart camilladsp.service     # links are rebuilt by the router within a second
systemctl --user stop theater-router.service    # stop auto-routing (mpv then plays direct, no EQ)
./scripts/route-mpv.sh status                   # manual routing helper (only while the router is stopped)
```

`route-mpv.sh on|off` is the older manual tool. While the router runs it will undo `route-mpv.sh off` within a
second: use `eq off` instead.

## After a reboot

Nothing to do. To confirm: start a film, run `eq status`. It should say audio goes through CamillaDSP. If the
USB interface enumerated under a different name, see [troubleshooting.md](troubleshooting.md).

## Backups

The tuning lives in a few small files. Keep them in this repository and push regularly:
`scripts/set-eq.py` (presets and alignment table), `configs/`, `docs/`.
Outside the repository, back up `~/.config/camilladsp/config.yml` (regenerable with set-eq.py), the mic calibration
file, and the player configuration: `~/.config/omniphony/` (config.yaml, overlay-prefs.conf), `~/.config/mpv/` (input.conf,
script-opts, scripts) and `~/.local/bin/mpv-atmos`. There is no `mpv.conf`.

## Re-tuning checklist

Redo measurements if any of these change: speaker positions, listening seat, Z906 sub level or placement, room furniture,
USB interface, or CamillaDSP chunk size. Method: [measurement.md](https://github.com/praveenchandrahas/Roomtone/blob/main/docs/measurement.md). Order of work: bass voicing,
then delays, then levels, then tone, then heights.
