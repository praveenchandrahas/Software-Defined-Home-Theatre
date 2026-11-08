# Spatial-Lab: a 3D listening test bench

[Spatial-Lab](https://github.com/praveenchandrahas/Spatial-Lab) (added 2026-11-08, [its own docs site](https://praveenchandrahas.github.io/Spatial-Lab/)) is the part of this project for *listening* to the room. The other repositories play films and measure the room; this one moves a test sound around the real speakers on demand, so panning, height, distance cues and phantom imaging can be heard rather than inferred from a sweep.

**Evidence level, first.** Tested in simulation (30 automated tests, and the page in a headless browser). **Not yet run on the rig**: real sound through PipeWire, the links to the interface and to CamillaDSP, and anything about how it sounds. Its "predicted image" is computed from the speaker gains, not measured. See [Status](status.md).

## What it does

- A web page (Three.js, served from 127.0.0.1) shows the room with the seven speakers placed from the author's measured directions. Drag the amber object (Shift or a tick box for up and down), or play a preset path, record one by dragging, replay it, and change the speed.
- Sound: pink noise (high-passed at 200 Hz so the satellites get no bass) in bursts or continuous, or any audio file ffmpeg can read.
- Panning: VBAP in 3D over the speaker directions, including the two ceiling speakers, with an optional source size, or "nearest speaker" for comparison. The sub output is never used.
- Distance cues: level against distance, air absorption (with a multiplier, because the real effect over a few metres is nearly inaudible) and optional Doppler.
- Phantom imaging ("phasing"): choose any set of speakers and give each its own trim, delay (0 to 50 ms) and polarity; the Labs panel sweeps delay, level and width and explains what to expect (summing localisation under about 1 ms, the precedence effect up to about 30 ms, comb filtering, out-of-phase pairs). The text is textbook guidance, not a measurement of this room.
- Image width: a Width control mixes in decorrelated copies of the signal across the speakers.
- Identify: plays each speaker in turn, to prove the channel map.

## How it connects to the rest of the chain

```
page (Three.js)  --JSON/WebSocket, 127.0.0.1-->  Python engine  --8 channels, pw-cat-->  PipeWire
                                                                                             |
                                          Direct:  the USB interface's playback ports        |
                                          Through: camilladsp-capture (the same input mpv uses)
```

- **Through** puts it in the same place as a film: CamillaDSP applies the bass EQ, the delays and trims and the bass management. In this mode its own distance alignment is off by default because CamillaDSP already aligns the speakers.
- **Direct** skips CamillaDSP and goes straight to the interface, with its own optional distance alignment (delay and gain from the layout distances). It therefore sounds different: no bass management, EQ or trims.
- Links are made explicitly with `pw-link`, the same way Roomtone's `tone-test.sh` does it. The router in linux-theater-dsp is not involved; stop mpv first (the check command warns if mpv is playing).
- It reads its own layout file (`spatial_lab/layouts/author-5.1.2.yml`), not Roomtone's. Sharing one file is on the [roadmap](roadmap.md).

## Safety

It starts muted. The master level is clamped to a ceiling read from its config file at start (-40 dBFS until the author raises it with `spatial-lab set-ceiling`); the page cannot change it. Unmute fades in over 3 s; Esc or the PANIC button silences in 20 ms; the engine mutes if the page stops answering for 4 s or the last page closes; level changes are slew-limited; the LFE output is silent. No per-channel hard limit is used (the author's choice). It listens on 127.0.0.1 only and rejects requests with a wrong Host or Origin header. Start with the amplifier volume low.

## Running it

```
./scripts/clone-all.sh          # clones it beside the other repositories as spatial-lab
cd ../spatial-lab
python3 -m spatial_lab check    # the USB sink should read "present"; CamillaDSP "present" for Through
python3 -m spatial_lab serve --open
```

`python3 -m spatial_lab serve --backend null` runs everything silently, for trying the page without the rig. `render` writes an 8-channel WAV, one WAV per speaker and a plot, playing nothing. Needs `python3-numpy python3-scipy python3-aiohttp python3-yaml ffmpeg pipewire-bin`. Its tests run with `scripts/test-all.sh` (they need pytest).

## Known gaps

- The USB sink name in its layout file did not match the author's machine at the first check because the interface was not connected; it must be confirmed with the interface present.
- An older `pw-cat` without `--raw` is handled by streaming a WAV header; checked with ffprobe, not yet on that `pw-cat`.
- Provisional geometry: the heights' distance, the ceiling height, the seat-to-back-wall distance, and the surround distance (3 ft stated; the CamillaDSP delay and trim for them suggest about 5 ft). They affect only the 3D drawing and the Direct-mode alignment.
- Both ceiling speakers are ahead of the seat, so an object directly overhead lands on the heights plus the surrounds; height is level-only, with no spectral cue.
- A browser tab left in the background for minutes may have its timers throttled enough to trip the watchdog; the result is a mute.
- Not done: microphone verification, an A/B against Omniphony's own object test, adding the `.deb` to `versions.lock` and the `sdht` meta package.
- Installing: the `.deb` is on the Spatial-Lab release page (`sudo apt install ./spatial-lab_0.1.0_all.deb`; installed by the author on 2026-11-08, and `spatial-lab check` found `pw-cat`, `pw-link`, `ffmpeg` and CamillaDSP; it stopped at the missing USB sink because the interface was not connected).
