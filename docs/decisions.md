# Design decisions

Short records of why things are the way they are. Format: decision, reason, what would change it.

## D1. 5.1.2 and nothing bigger
10 x 10 ft room with no space behind the seat, so rear and extra height speakers (7.1.4, 5.1.4) are not practical.
Side-surround placement for SL/SR. *Revisit* if the room changes (a new room is planned later; see roadmap).

## D2. DSP is CamillaDSP inside the PipeWire graph
CamillaDSP exposes `camilladsp-capture` / `camilladsp-playback` as PipeWire nodes, so mpv, the DSP and the hardware
stay independent and rewireable (qpwgraph shows it). *Cost:* links to CamillaDSP are lost on every restart, which is
why a router exists.

## D3. EQ is cut-only
Nulls cannot be filled by boosting; boosting also eats headroom and risks clipping. All presets only cut, and the
alignment trims only lower levels. *Consequence:* EQ on is quieter than EQ off.

## D4. Bass is voiced above flat, on purpose
A flat correction sounded lean and hollow for a listener who wants thump. Presets target a deliberate hump (8-20 dB above
the mids), then trim the boomy part by frequency (`drone` sets). *Revisit* if the speakers or the seat change.

## D5. Separate drone from thump with narrow cuts
In film scores the boomy drone (63-92 Hz) and the thump (56-63 Hz) occupy different frequencies, so static narrow cuts
at 72 and 84 Hz work without a dynamic processor. *Limit:* it also dents any music note at those frequencies.

## D6. Align to the farthest speaker
Delays can only be added, so every speaker is delayed to match the farthest (FR); the heights end up with the largest
delays but nothing else depends on them. (First idea, delaying the whole bed for the heights' sake, was rejected: get the 5.1 bed right first.)

## D7. `--align=bed` leaves the heights alone (superseded by D14: the owner now runs `--align` with the heights)
The owner is fine with heights slightly hot and mostly relies on the bed for imaging. The height delay and trim numbers
are measured and stored (`ALIGN`) but only applied with `--align` (no value).

## D8. Do not invert the centre
An early analysis suggested it was inverted; the proper pair test showed all speakers in phase. `--invert` is kept as a tool.

## D9. Measure with a separate mic device, remove clock drift in the fit
The mic is on a different USB device than playback, so timing uses a chirp train and a least-squares fit that separates
clock drift from speaker delay. REW's own arrival times (no timing reference) are not used.

## D10. The router polls instead of using WirePlumber rules
CamillaDSP is a *stream* in PipeWire, not a sink, so a rule that points mpv at it would leave mpv silent whenever CamillaDSP
is down. A small poller with make-before-break and an automatic direct fallback makes "never silent" a property of the
design. *Cost:* up to half a second of direct (un-EQ'd) sound when mpv starts.

## D11. `eq off` bypasses everything
Off means mpv goes straight to the USB interface: no bass EQ, and no delays or trims either. A "bass EQ off but keep
alignment" mode would need CamillaDSP to reload its config live while keeping its ports, which has not been verified. *Revisit* if that is wanted.

## D12. Z906 knobs are fixed references
The tuning assumes the Z906 sub level as it is. Change the master volume freely; change the sub level only with a re-measurement.

## D13. No night preset
This rig is for full, object-rendered film sound. For late-night or neighbour-sensitive viewing the owner switches to the family TV and soundbar instead of adding a quiet-hours preset (reduced bass, compressed dynamics) here. *Revisit* only if that changes.

## D14. The heights get bass management and tone-matching in CamillaDSP
Heights barely reproduce bass; bed channels already feed the sub via the Z906. A 9th internal channel (RL+RR, low-passed at
140 Hz LR4) is added to the LFE at 0 dB and RL/RR are high-passed at 140 Hz. Chosen from sweep run 1: best fit to the bed's
response over 40-400 Hz; delay and polarity do not matter, so none are applied (`--heights-delay`, `--heights-invert` exist).
*Cost:* more bass in the sub from height-heavy scenes (back it off with `--heights-lfe=-2` if the sub is overloaded).

## D15. Height tone filters correct only what both heights agree on
Three filters plus a trim, fitted to the bed mean; narrow, channel-specific features are left alone because a one-seat,
one-microphone measurement changes them by 3-7 dB when the mic moves. Trim +1.0 dB is a compromise between two runs.

## D16. A standing profile with automatic start
`./set-eq.py` with no arguments is the standing profile (`DEFAULT_ARGS`). The profile lives in CamillaDSP's config file, so it
survives reboots; `eq ensure` (called by `mpv-atmos`) starts CamillaDSP and the router if either is down. *Revisit* if more
players than mpv-atmos should start the services.

## D17. Do not chase the sub below 30 Hz in the apartment
Usable output ends near 30 Hz and film content under 25 Hz is rare. Revisit when moving to the independent house.

## D18. Spatial-Lab: a separate repository, a local Python renderer, ceiling set by hand
*Decided 2026-11-08.* The 3D test bench is its own repository so it can be used without the rest, and the sound is made by a local Python engine behind the web page rather than in the browser or through Omniphony's own object test. *Reasons:* the browser cannot address eight outputs or choose between the interface and CamillaDSP; the engine can pace blocks, enforce a level ceiling the page cannot change, and write the same blocks to a file for offline renders and tests; a panner of its own shows the panning maths on this exact layout. *Safety:* starts muted, ceiling -40 dBFS raised only by editing the config, 3 s fade-in, Esc mutes, mutes when the page goes away, LFE never used, no per-channel hard limit (the author's choice). *Local only:* 127.0.0.1, with Host and Origin checks, no LAN listener (the author's choice, as for the status page). *Cost:* a second layout file next to Roomtone's, and a second panner next to Omniphony's; *revisit* if they disagree on the same speaker.
