# The stack against the open-source / DIY frontier (software only), October 2026

Written 2026-10-25. Scope: software signal path and processing only; hardware is mentioned only where it caps what software can do.
Subject: the SDHT stack as documented in `README.md`, `docs/technical-writeup.md`, `docs/architecture.md`, `docs/status.md`, `docs/decisions.md`
(plus `docs/installation.md`, `docs/measurement.md`, `docs/roadmap.md` and the scripts where a detail mattered).

**How to read the labels.** `[V]` = verified: I read it in a source this session. `[A]` = author, vendor or poster claim, not independently checked.
`[I]` = my inference. Where I could not find evidence I say so. The rating words mean: **frontier** = what the best open/DIY builders do, or ahead of
anything I could find; **advanced hobbyist** = better than most builds, short of the best; **standard** = what a competent enthusiast normally does; **behind** = a
common practice or capability that is missing.

## 1. Verdict table

| # | Layer | Where it sits | Evidence in one line |
|---|-------|---------------|----------------------|
| 1 | Live Atmos object decode and render (harletty-bridge + Omniphony + mpv-omniphony) | **Frontier** (for open source on Linux), as an integrator of someone else's frontier work. Version lag is a risk | The only open live Atmos path I found that is actively developed; Cavern's author says real-time Atmos is not available. Rig runs liborender 0.3.0 against upstream v0.7.0 |
| 2 | Format coverage (DTS:X, IAMF/Eclipsa, Ambisonics) | **Standard** (Dolby only, in practice) | Bridge and Omniphony advertise DTS:X and experimental IAMF; the rig has verified neither. Ambisonics is not part of any film path I found |
| 3 | Room-correction method (one seat, parametric IIR, cut-only, voiced target) | **Standard** for the method; **behind** the advanced DIY norm (multi-point average, FIR or mixed phase) | Linux/Z906/CamillaDSP builders already publish FIR workflows with averaged measurements; commercial tools use multi-position 3D measurement |
| 4 | Measurement and verification tooling (through-DSP sweeps, STI, reflections, drift fit) | **Advanced hobbyist**, with a validation caveat | Unusual breadth for a hobby rig; the author states the analysis code was AI-written, checked against simulations and REW exports and used in his real room, but not repeated by another person or a second tool |
| 5 | Multi-seat optimisation | **Not attempted, by design** (roadmap says so) | Fine for one listener; every frontier tool I found optimises over several positions |
| 6 | Bass integration of the existing Z906 sub | **Behind** | Own data: sub arrives 6 to 7 ms after FL, group delay near 15 ms, not compensated; judged inaudible as a delay at this seat (not listened-tested), but sub-versus-main phase at the crossover is unsettled and is table stakes in sub threads |
| 7 | Second sub and clock handling (T670 sub, drift tracker, no optimiser) | **Plan only.** Drift tracker has no precedent I could find; the missing optimiser is the standard approach | MSO and Dirac Live Bass Control are the norm; no published drift-tracking of a soundbar sub found; the tracker is untested on the rig |
| 8 | Stereo and 5.1 upmix (own adaptive ambience engine) | **Advanced hobbyist prototype**, unvalidated | Same architecture family as published and commercial upmixers; evidence is synthetic tests only, no comparison with Dolby Surround, Neural:X or Auro-Matic |
| 9 | Video (mpv gpu-next, tone mapping, BT.1886, 60-nit target) | **Standard to advanced hobbyist** on Linux; **behind** the madVR reference only on instrument-based calibration | Settings are sensible, fully scripted and the 60-nit peak was tested by the owner (by eye, not by instrument); mpv also tone-maps per frame (`hdr-compute-peak`, whether active in the wrapper is unconfirmed). Gaps: no meter-based calibration, libplacebo 6.338 vs current 7.360. DV FEL is not decoded, which the owner judges irrelevant (a 60-nit projector cannot show what the enhancement layer restores) |
| 10 | Audio routing and control plane (PipeWire, CamillaDSP, router, profile switching) | **Advanced hobbyist** | Working make-before-break routing and per-stream profile switching; peers report struggling with basic PipeWire-CamillaDSP wiring. Most of it is tested in simulation only |
| 11 | Currency of the software versions | **Behind** | PipeWire 1.0.5 (1.6.0 released 2026-02-19), libplacebo 6.338.2, Omniphony 0.3.0 vs 0.7.0 |

Bottom line `[I]`: it is on the frontier where the frontier is thin (live object audio on Linux), advanced where the author built tooling, and standard or
behind in the layers where the best DIY builders pay for multi-position measurement, FIR and sub optimisation. For a 10 x 10 ft, bass-forward, single-seat
room the biggest gap that matters is bass at the seat, not the object renderer or the video chain.

## 2. What I could and could not reach

Read in full or in part this session: Doom9, AVForums, AV Nirvana, Audioholics-hosted, diyAudio, StereoNET, miniDSP, Harman (Welti), vendor pages (Dirac, Trinnov
reviews, madVR retailer), GitHub pages for Omniphony and harletty forks, Phoronix, PipeWire NEWS, mpv issue tracker, DAFx and IEEE listings.
**Not reached:** AVS Forum threads (search returned none that I could open), Reddit r/hometheater and r/diyaudio (no usable results), Head-Fi Science Forum (searched,
nothing relevant), Quadraphonic Quad threads on Omniphony (page failed to load), the Cavern project's own website (pages returned empty text; I used GitHub mirrors, NuGet and
forum posts instead), AUR package pages (blocked by a bot filter). Any claim below about those communities is therefore not made.

## 3. Per-layer evidence

### 3.1 Live Atmos object decode and render

**What the rig does** `[V, from repo docs]`: harletty-bridge decodes TrueHD and E-AC-3 JOC; Omniphony renders objects with VBAP to a measured 5.1.2 layout; mpv-omniphony
(mpv 0.41.0 built from source) hands 8 float channels at 48 kHz to PipeWire.

**What the frontier looks like**

- Omniphony: real-time object renderer, VBAP plus a "volumetric" backend, any speaker count (tested to 128 per the project), pluggable decoder bridges, OSC control,
  a native Studio app, PipeWire/ASIO/CoreAudio backends, GPL-3.0, v0.7.0 latest, 103 stars. The author calls it "a nights-and-weekends project, not a product", and
  says CI skips tests that need a sound device or PipeWire, so those backends are compiled but not exercised in CI `[V]` (GitHub page, project site).
- It was announced on Doom9 on 20 May 2026, with TrueHD and E-AC-3 Atmos support confirmed by the author on 8 to 9 June 2026; he also said it was not yet stable `[V]`.
- Cavern (VoidXH), the long-standing open Atmos engine: 583 stars, last push 15 Sep 2026, NuGet 2.1.0 (16 Jan 2026) `[V]`. Its author wrote in Nov 2024 that real-time true Atmos
  decoding is not available and that the real-time option, the Cavernize VST under Equalizer APO, is an upconverter. A GitHub issue proposing a real-time pipe host
  was closed unimplemented ("until I find a good implementation point in any player") `[V]`. TrueHD decoding arrived in Cavern in Aug 2025 via truehdd `[V]`.
  Nothing I read mentions Linux support for Cavern's real-time paths.
- truehdd (Rainbaby, Aug 2025) is the open TrueHD Atmos decoder both Cavern and the harletty CLI build on; its author said a renderer is out of scope `[V]`.
  harletty's README says its CLI is a fork of truehdd and that 85 % of shared lines are byte-identical `[A, via GitHub page fetch]`.
- Other Linux attempts exist but are small: `EvanSunde/Atmos-Linux` (a Rust port of Cavern's E-AC-3 JOC path plus a TrueHD panner, mpv only, no seeking, 7 commits, 0 stars)
  and a Stremio fork using Omniphony `[V]` (page content). I found no AVS Forum or Reddit evidence of anyone else running a live object chain through a full DSP and
  routing layer as this rig does.
- Format breadth upstream: the Atmos-Web-Decoder fork lists TrueHD, E-AC-3 JOC, DTS, DTS:X, Auro-3D over DTS-HD MA and IAMF/Eclipsa; Omniphony labels IAMF support experimental `[V, README of fork]`.
- Commercial reference: StormAudio and Trinnov decode Atmos in hardware; Trinnov's Altitude16 is listed at about 13,000 GBP in one review and 18,000 USD in another `[A]`. Not a DIY comparator, only context.

**Where the rig sits.** Frontier, because the frontier is one open project and the rig runs it end to end on Linux. Credit belongs mostly upstream, which the README
says openly. The user's own contributions that I could check: a bug filed and a packaging fix said to be merged `[A]` (README; I could not find the pull request).

**Caveats**
- Version lag `[V]`: rig records liborender 0.3.0 and bridge API 0.3.0 (built Jul/Aug 2026). Upstream v0.6.0 notes say bridge API moved 0.3 to 0.4 and "requires harletty-bridge 0.8.0, update together"; v0.7.0 lists liborender ABI 0.12 and bridge_api 0.6.x.
  The rig's harletty library "carries no version". An update is a coordinated change of engine, bridge and player.
- DTS:X on the rig: a DTS:X clip played with sound on 2026-10-25 (USB interface not connected); decoding as DTS:X objects was later confirmed by the owner on a real DTS:X film (the date of that play was not recorded; the checklist item was ticked off on 2026-10-29) `[V, docs/todo-fill-in.md]`.
- No measured latency or CPU cost of the live decode and render chain `[V, todo list]`.
- Rendering fidelity is unvalidated `[I]`: VBAP onto two ceiling speakers is a coarse height model; I found no comparison against Dolby's own renderer by anyone, including the author.
- Omniphony's own docs list no room correction, bass management or distance compensation in the engine `[V]`; the rig correctly puts those in CamillaDSP.

### 3.2 Immersive formats beyond Dolby: IAMF/Eclipsa, SAF, Ambisonics

- Eclipsa/IAMF: announced by Google and Samsung on 15 Jan 2025, royalty-free, libiamf as reference renderer, iamf-tools for authoring `[V]`. FFmpeg gained an IAMF demuxer and muxer in Dec 2023 (no decoder or renderer in that change) `[V]`.
  Omniphony's IAMF support is experimental and uses its own Matroska and IEC 61937 carrier designs `[V]`. For a rig that plays Atmos remuxes there is no content reason to prioritise it `[I]`.
- Ambisonics and SPARTA/IEM-style decoders are mature research and production tools (SPARTA has an AES paper; IEM suite is a plugin bundle) `[V, search listings only]`. I found no case of a
  home-cinema builder using them for Atmos film. Atmos is object-plus-bed, so VBAP to the real layout is the direct route `[I]`.
- I did not find a "SAF" (Spatial Audio Framework) home-theatre build; SPARTA's authors use it as the underlying library `[unverified]`.

### 3.3 Room-correction method

**Rig** `[V]`: REW sweeps with a Dayton iMM-6S at one seat; cut-only parametric IIR (about 10 filters, Q about 4 to 8) in CamillaDSP; deliberate bass hump; no FIR, no mixed phase, no multi-seat; trims and delays from a drift-removing chirp fit.

**Frontier practice**
- Linux, Z906 and CamillaDSP is an existing user class: on AV Nirvana, user `linuxonly` (Fedora, PipeWire, WirePlumber, Z906) asked for and received corrections to a REW to CamillaDSP FIR guide using pink noise, a moving microphone and variable smoothing, Aug to Sep 2025 `[V]`.
  That user also reports trouble wiring PipeWire to CamillaDSP at all (Sep 2024), so the rig is ahead on integration and behind on filter method `[V]`.
- REW plus rePhase guide (OCA, Jan 2020): measure the seat plus four points 25 to 30 cm away, vector-average, 65,536-tap 48 kHz FIR, excess-phase correction, and leave phase EQ alone below 100 Hz because it can ring `[V, author claim]`.
- Acourate v3.1 review (Archimago, Aug 2024): bass pre-filter on the unsmoothed room response below about 277 Hz, inter-channel phase alignment; the reviewer found the phase-alignment benefit "at best subtle" and could not tell Acourate from Audiolense by ear `[V]`.
  A forum comparison says Dirac filters are about 20 ms (roughly 4,000 taps at 96 kHz) against 64k taps typical for Acourate `[A]`.
- Trinnov Optimizer: tetrahedral 3D microphone, measurements from several positions, "65,000+ taps at 96 kHz" per a forum review `[A]`; one review says the processor handles multiple subs and per-speaker crossovers `[A]`.
- Dirac Live for PC and Mac: Room Correction 499 USD, Bass Control 299 USD, ART 299 USD; the page lists PC and Mac only, not Linux `[V]`.
- Academic caution: a USC paper (2002) studies how far a spatial-average equalisation zone extends and finds it shrinks with distance and frequency `[V]`. A single-point fit gives no such zone `[I]`.

**Where the rig sits.** Cut-only bass EQ below the modal region is the textbook-safe choice (a null cannot be filled by boosting; the repo says so in D3). I found no source arguing against it `[I]`.
It is **standard** for the method. It is **behind** advanced DIY on two points, both cheap in software: the fit is from one microphone position, and the cuts are narrow.
The repo's own repeatability data say single bins move 3 to 7 dB when the mic moves a few centimetres (README, Uncertainty). Narrow cuts such as Q 8 at 72 Hz fitted at one point are exactly the
filters that data says are least robust `[I]`. Counter-argument: the owner is one listener at one seat and verified the result by listening; a narrow cut that works at that ear is not wrong for that ear.

Room context `[I]`: for a 10 x 10 x about 8 ft room the whole 25 to roughly 250 Hz region is modal (Schroeder frequency from 2000 * sqrt(RT60/V) with an assumed RT60 of 0.35 s is near 250 Hz; RT60 is not measured here, the repo has an RT60 estimate in the dialogue kit I did not check). The first axial mode of 10 ft is near 56 Hz, matching the measured 56 to 68 Hz peak `[V, technical-writeup]`.

### 3.4 Measurement and verification tooling

Evidence in repo `[V]`: sweeps through CamillaDSP with sync chirps on a second clock, STI estimate, early-reflection analysis against ITU-R BS.1116, polarity pair tests, a drift tool, 51 router checks, and a status table with Verified / Measured / Not tested levels.
Peers mostly use REW alone. The honest labelling (verified vs simulated) is better than most build logs I read `[I]`.
Limits: README says the analysis code was written with an AI assistant, checked against simulations and REW exports and used on real recordings in the author's room, but not repeated by another person or a second tool `[V]`. STI is a STIPA-style estimate without masking, one microphone, no absolute level calibration `[V]`.
The rig measures the full chain, which REW cannot do directly (REW sends its sweep to the sound card; stated in measurement.md) `[V]`. Rate: **advanced hobbyist**; it would move up with an independent cross-check against REW on a few key results.

### 3.5 Multi-seat optimisation

Not attempted by decision (roadmap: "multi-seat averaging (tuned for one seat)") `[V]`. MSO supports several measurement groups with weights and recommends at least as many positions as subs `[V, miniDSP page]`.
Dirac Bass Control claims consistency across seats `[A]`. Harman's Welti paper is about seat-to-seat variance `[V]`. For a one-listener room this is a trade, not a defect `[I]`.
One consequence: the decision also means the filters have no estimate of how fragile they are, which section 3.3 already raised.

### 3.6 Subwoofer integration (existing Z906 sub)

The rig's own measurement `[V]`: the sub arrives 6 to 7 ms after FL with group delay near 15 ms at 50 to 100 Hz; the LFE delay is still 0.20 ms; the 6 to 7 ms is judged inaudible as a delay at this seat (reasoned from thresholds, not listened-tested); the open question is summation at the crossover, recorded in status.md.
The Z906 gives the sub the bass of every channel as well as the LFE, so all bass paths share the Z906's internal crossover `[V, architecture.md]`; software can shape what goes in but cannot separate the sub's path `[I]`.
Peer practice: comparing a sub's delay relative to a main speaker with the same mic position and room correction disabled is the recommended way to read sub timing in REW `[V, Arendal article]`; sub-versus-main phase at the crossover is the standard thing to settle first `[V, miniDSP thread]`.
Rate: **behind** on this one item, and it is the baseline for everything in 3.7.

### 3.7 Second subwoofer, clock handling, optimisers

**Rig plan** `[V]`: spare Samsung HW-T670 sub fed through the soundbar over HDMI (a separate clock), `tools/drifttest/` with chirp pairs in one mic recording that reports ppm drift, jitter and steps; no multi-sub optimiser; status says the tool has been run on simulated recordings only.

**Frontier practice**
- MSO (Andy C): free, optimises several subs against several measurement groups with per-sub gain, delay, parametric EQ, high-pass, polarity and all-pass; exports biquads; demonstrated by miniDSP only with their hardware, FIR not mentioned `[V]`. I could not read the author's own page or the AVS Forum thread, so this is the vendor's app-note description.
- Dirac Live Bass Control automates sub time alignment and levelling; one forum user who used MSO first says it "greatly simplifies things" but calls Dirac a black box (Jul 2023) `[A]`.
- A 12-sub project on AV Nirvana (Apr 2025) used MSO plus Dirac Bass Control, with no reported numbers and no replies `[V]`.
- Theory: Harman's Welti simulation (20 x 24 x 9 ft, 16 seats, after EQ): one optimised sub 3.9 dB seat-to-seat standard deviation, two subs at opposing wall midpoints 1.3 dB, four at wall midpoints 0.9 dB; "no justification for using more than four"; results assume coherent drive from one bass channel `[V]`.
  Different room size and a multi-seat metric; it supports two subs as the best cost-benefit, not the exact gain here `[I]`.
- Wireless subs: a miniDSP thread (May 2025) cites a transceiver rated about 20 ms and says the processor will not compensate automatically; the correction is a manual delay `[A]`. A June 2025 thread asked how to measure wireless-sub latency and got only measurement tricks, no figures `[V]`.
  I found no posts about wireless or soundbar subs drifting against a wired sub over time. That means either nobody reports it or nobody measures it; I cannot tell which.
- Clock domains: PipeWire's man page says follower devices are resampled adaptively unless nodes share a `clock.name`, and that same-device nodes are assumed to share a clock in Pro Audio mode `[V]`.
  On diyAudio (May 2026) a poster argues PTP alone does not align a DAC's output clock, so "some deliberate synchronization must be provided" `[A]`. Dante or AES67 would solve it with real PTP hardware; neither is a software-only option for a soundbar sub `[I]`.

**Where the rig sits.** The drift tracker is a sensible, original idea: a mic recording of paired chirps measures the thing that matters (end-to-end phase stability of the sub against the main sub) without needing access to the soundbar's clock `[I]`.
Arithmetic, hypothetical: if the two paths drifted by 50 ppm the relative delay would move 3 ms per minute, a quarter period at 60 Hz in about 80 seconds `[I]`. So the tool's job is a go/no-go gate; if the drift is real, a fixed delay cannot hold the phase `[I]`.
What I could not establish: how PipeWire's adaptive resampling behaves for relative phase at 50 to 100 Hz, and whether the soundbar's wireless leg to the sub has fixed buffering. Both are measurable with the tool already built.
No optimiser and no measurement of the T670 sub's usable band yet (status "later") `[V]`. Rate: plan only; do not score until measured.

### 3.8 Upmixers

**Rig** `[V]`: `scripts/upmix_engine.py`, a streaming STFT that separates direct sound from ambience per time-frequency tile (smoothed 2 x 2 covariance, directness D), sends only ambience to surrounds and heights with decorrelation and Haas delay; falls back to a fixed matrix. Self-reported synthetic result: on harmonic notes hard left, leak minus ambience improves from +3.6 dB (fixed matrix) to +21 dB; on dense noise no gain (+4.0).
"About 4 % of one core and 21 ms" is for the engine only and was not re-measured on the live rig; the engine has never run against real PipeWire `[V, README]`.

**What exists**
- Commercial: Dolby Surround upmixer, DTS Neural:X, Auro-Matic (Trinnov lists all three; one reviewer prefers Dolby Surround for 5.1 and 7.1 sources) `[A]`.
- Open or semi-open: the FFmpeg `surround` filter has had upmix support for 3.0, 2.1 and 5.1 layouts since 2017 `[V, patch]`. SotF's upmixer plugin does FFT direct/ambient decomposition, VBAP, decorrelation, ERB grouping, transient detection and optional voice routing, with output to 5.1.2 through 9.1.6; I could not find its licence `[V, docs page]`.
  Cavern lists real-time upmixing `[V, review post]`. Its quality is not assessed in anything I read.
- Research: S2X-Net (IEEE TASLP, Oct 2026) reports a 50-subject MUSHRA-style test and claims "near human-made upmixing results" `[A]`; PAEDB (DAFx26) trains networks to imitate DSP primary-ambient extractors and reports a 12-person listening study in which a DSP reference ranked first `[V]`.
  Both use listening tests as the evidence standard; the repo's evidence for upmixing is synthetic metrics `[I]`.

**Where the rig sits.** The design is in the same family as published and commercial work, which is a fair compliment `[I]`; the evidence is far weaker. Rate: **advanced hobbyist prototype**. I did not find any independent number to say it is better or worse than Neural:X or Dolby Surround. The cheapest credible test is a blind A/B by ear on real music and speech clips, which the repo lists under "upmix by ear".

### 3.9 Video: tone mapping, calibration, DV

**Rig** `[V]`: mpv 0.41.0, `--vo=gpu-next --gpu-api=vulkan`, VAAPI, `--target-prim=bt.709 --target-trc=bt.1886 --target-peak=60 --tone-mapping=bt.2390`, Mitchell downscaling with linear and corrected downscaling, debanding, on a BenQ W1070 and a painted 107-inch screen; libplacebo 6.338.2 (system library).
The 60-nit target "came from measuring the projector's real output" `[A]`; no colorimeter is owned and the method is not described in the docs I read.

**What exists**
- gpu-next vs gpu (mpv wiki, possibly dated): `tone-mapping=auto` selects `spline` rather than `bt.2390`; gpu-next gives frame-exact peak detection and options `--hdr-peak-percentile`, `--hdr-contrast-recovery`; Dolby Vision is supported "only reshaping" `[V]`.
  The rig sets bt.2390 explicitly and does not set the peak-detection options; the effective defaults on mpv 0.41.0 I did not verify `[I]`.
- Dolby Vision profile 7 FEL: in an undated mpv issue maintainers say "RPU values are used. EL is not decoded at all" `[V]`. The rig's test files were profile 7.6 MEL, where this does not matter `[V]`. I could not find current (2026) status; an AUR package named `mpv-omniphony-fel` exists but I could not read it `[unverified]`.
  For an SDR 1080p projector the FEL gain is small `[I]`.
- madVR (Envy) is the reference for projector HDR: a retailer article (Apr 2026, last modified Jun 2026) says it is real-time, frame by frame, calibrated to room, screen and projector with hours of per-room measurement `[A, marketing]`. madVR is Windows or Envy hardware; there is no Linux build `[I]`.
- Instrument-based calibration on Linux is ArgyllCMS/DisplayCAL to a 3D LUT or ICC profile, which mpv can consume; I did not confirm mpv's LUT option names this session (from memory `--lut` and `--icc-profile`) `[unverified]`. A DisplayCAL forum post (2021) shows people pairing madVR dynamic tone mapping with a Rec.709 3D LUT on SDR projectors `[V]`.
- libplacebo: current tag seen is v7.360.1 (v7.360.0 listed as eight months old on a release aggregator); the rig uses 6.338.2 `[V]`.

**Where the rig sits.** Everything in the wrapper is a defensible, scripted setup, ahead of default mpv. The 60-nit peak was tested by the owner (corrected 2026-10-25; an earlier draft called it a guess), and mpv computes the HDR peak per frame, so the tone-mapping method is comparable in kind to madVR's. Without a meter, though, the BT.1886 target and the display calibration are not instrument-verified, so the
picture is neither verified nor frontier. Projector black level matters for BT.1886 and for a grey-cloud lamp issue the repo already notes `[V]`. Rate: **standard to advanced hobbyist** on Linux; **behind** the madVR reference. Not where this user's priorities lie.

### 3.10 Linux audio routing and control plane

- Stack versions `[V]`: PipeWire 1.0.5 and WirePlumber 0.4.17 on Ubuntu 24.04; PipeWire 1.6.0 was released 2026-02-19 (1.6.6 exists in the Debian NEWS I saw); 1.6 raises max channels to 128 and adds resampler window options, nothing specific to drift.
- CamillaDSP 4.1.3 on PipeWire: peers report 4.1.0 in 2026 `[V, diyAudio]`. CamillaDSP is positioned as the engine for FIR and IIR crossovers and room correction, mostly in two-channel and multi-way music systems `[V, StereoNET and diyAudio threads]`; the threads I read had no surround home-theatre use of it.
- The rig's router (0.5 s polling, make-before-break, direct fallback, per-stream profile) plus `eq` switch is custom. Commercial processors do format-aware preset switching natively (Trinnov stores up to 29 presets) `[A]`.
- Status: the router, profile switching and adaptive engine are simulation-tested; reboot, mid-film switch and live engine on the rig are open `[V]`. Added latency is estimated 20 to 45 ms, owner reports no lip-sync issue, not measured `[V]`.
- The Fire Stick bypasses all of it (TOSLINK to the Z906) `[V]`, so streaming content gets no correction. In a processor-centred build everything passes the DSP `[I]`.

Rate: **advanced hobbyist**. Version currency is the weak point, and the Fire Stick path is a coverage gap rather than a technique gap.

## 4. The five highest-value steps

Ordered for a 10 x 10 ft room where bass modes dominate, the owner is bass-forward, one seat, and does not chase perfection. Each is software or measurement only.

1. **Re-measure bass at 5 to 9 points around the seat and re-fit from the average.** Use REW itself (independent of the repo's scripts), weight the main seat most, then compare the average to the one-point fit. Keep the cuts that survive; widen or drop those that move 3 dB or more.
   Why first: it addresses the main problem (modes) and the weakest piece of evidence (one-point, Q 8 cuts) at near-zero cost, and it sets the baseline MSO needs anyway. Expect the narrow 72/84 Hz cuts to be the first test.
2. **Settle the existing sub against the satellites.** The 6 to 7 ms offset and 15 ms group delay are your own numbers. With the sweep tool or REW's alignment view, try bed delay offsets and polarity at the crossover region and pick by measured summation and by ear (status.md already frames the question). Verify with a single repeat run.
3. **Run the drift test with the T670 path before buying any effort for it.** Measure ppm, jitter and steps over an hour and over a film-length run. If drift or steps are visible, skip the T670 sub or move the second sub onto the DAC's clock; if stable, proceed. This is a go/no-go costing one evening and uses a tool already built.
4. **If go, optimise the two subs with MSO on the multi-point set from step 1,** then paste the per-sub gain, delay, PEQ into CamillaDSP. The Welti simulation puts two subs at opposing wall midpoints close to four `[V]`, though it is a bigger room. In a 10 ft room a seat against the rear wall is a placement the simulation did not cover `[I]`; measure rather than copy.
   Check the T670 sub's usable band first (status.md already lists this): a small wireless sub may only help above about 40 Hz `[unverified, I did not find specs]`.
5. **Pin and update the player stack once the preflight run passes on the rig.** Move Omniphony, harletty-bridge and mpv-omniphony together (the project says versions must match), record versions, then measure CPU and latency of the live decode path (an open item in the docs). Consider PipeWire and libplacebo updates only if a problem appears; they are not where the audible gain is.
   If streaming from the Fire Stick is more than occasional, capturing its PCM output through the Vantec (status item 3) is the next candidate; I did not verify that the Fire Stick can output multichannel PCM `[unverified]`.

**Considered and left out.** FIR or mixed-phase correction: little gain for single-seat cut-only bass in a modal room, and phase EQ under 100 Hz can ring (OCA, `[A]`); revisit after step 1. Colorimeter and 3D LUT: real gain for the picture, not for a bass-forward priority. IAMF, DTS:X, Ambisonics: no content reason now. Upmixer validation: do the blind A/B by ear when convenient.

## 5. Unverified items (could not find evidence, or claim not checked)

- Reddit, AVS Forum and Head-Fi Science Forum threads: none read. No claim is made about what those communities do.
- Cavern's own documentation (QuickEQ features, real-time modes, platform list): pages returned empty. One AVForums poster says QuickEQ supports multiple independent subs and possibly mixed IIR/FIR filters `[A]`; I could not confirm it. Wikipedia says QuickEQ exports minimum- or zero-phase FIR `[A]`.
- MSO's own page, version history and whether it offers FIR output: not read.
- Omniphony v0.7.0 release notes in full, the exact date of v0.6.0 ("20 Sep", year not shown), rendering quality versus Dolby's renderer, latency and CPU of the live path, DTS:X on this rig.
- The 60-nit measurement method; the projector's real gamma; mpv 0.41.0's effective defaults for tone mapping and peak detection.
- Current (2026) status of Dolby Vision FEL in mpv/libplacebo; contents of the `mpv-omniphony-fel` AUR package.
- Whether mpv has `--lut` and `--icc-profile` as I recall; whether SotF's upmixer is open source.
- How PipeWire's adaptive resampling affects relative phase of a 50 to 100 Hz channel; whether the soundbar's wireless sub link has fixed buffering; the T670 sub's frequency range and power (search returned other models only).
- The user's room: dimensions disagree across docs (10 x 10, 10 x 11, 11 x 12 ft); RT60 not checked; my Schroeder estimate assumes 0.35 s.
- The README claim that a packaging fix was merged upstream.
- Whether "no one else uses a drift tracker" is true: I found no mention, which is weaker than absence.

## 6. Sources

Object audio and Atmos decode
- Omniphony repository: https://github.com/mgth/Omniphony
- Omniphony project site: https://omniphony.mgth.fr/
- Omniphony v0.6.0 release: https://github.com/mgth/Omniphony/releases/tag/v0.6.0
- Doom9, "Spatial Audio Rendering for Home Cinema" (20 May to 15 Jul 2026): https://forum.doom9.org/showthread.php?s=0e7b8ae61ea579d9441a1ed5cef5a87e&p=2031329#post2031329
- harletty-bridge (fork seen): https://github.com/v-lix/harletty-bridge
- Atmos-Web-Decoder (fork of harletty-bridge): https://github.com/aimeovv3-hue/Atmos-Web-Decoder
- Doom9, TrueHDD thread: https://forum.doom9.org/archive/index.php/t-186454.html and https://forum.doom9.org/showthread.php?p=2021628
- Doom9, Cavern/Cavernize thread: https://forum.doom9.org/showthread.php?p=1977210
- Cavern discussion 185 (real-time rendering): https://github.com/VoidXH/Cavern/discussions/185
- Cavern issue 201 ("The final boss"): https://github.com/VoidXH/Cavern/issues/201
- Cavern repository stats (mirror): https://gittrend.io/repo/VoidXH/Cavern
- Cavern on NuGet: https://www.nuget.org/packages/Cavern
- Cavern overview post (Audio File, Nov 2025): https://audio-file.org/2025/11/29/cavern-object-based-audio-engine-codec/
- AVForums, "Atmos decoding on a PC": https://www.avforums.com/threads/atmos-decoding-on-a-pc.2534199/latest
- Atmos-Linux: https://github.com/EvanSunde/Atmos-Linux
- Eclipsa Audio announcement: https://opensource.googleblog.com/2025/01/introducing-eclipsa-audio-immersive-audio-for-everyone.html?m=0
- FFmpeg IAMF merge (Phoronix): https://www.phoronix.com/news/FFmpeg-Immersive-IAMF
- SPARTA/ambisonics search listing (not read in depth): https://soundingfuture.com/tools/sparta

Room correction, subs, clocks
- miniDSP, MSO application note: https://www.minidsp.com/applications/home-theater-tuning/multi-sub-optimizer-ht-5-3
- Welti (Harman), "Subwoofers: Optimum Number and Locations": https://www.harman.com/Documents/multsubs.pdf
- AV Nirvana, Dirac Bass Control multi-sub thread: https://www.avnirvana.com/threads/dirac-live-bass-control-multi-sw-seeking-info.12274
- AV Nirvana, 12-subwoofer thread: https://www.avnirvana.com/threads/12-subwoofers-calibration-and-integration-in-ht-system-swarm-array-bass.15023/
- AV Nirvana, "Linux guide?" (REW to CamillaDSP FIR): https://www.avnirvana.com/threads/linux-guide.13946/post-117850
- AV Nirvana, CamillaDSP PipeWire on Fedora 40: https://www.avnirvana.com/threads/camilladsp-pipewire-config-fedora-40-help.14118/latest
- AV Nirvana, Trinnov Altitude review thread: https://www.avnirvana.com/threads/trinnov-altitude-review-five-features-that-set-it-apart-from-other-processors.15528/
- Sound and Vision, Trinnov Altitude16: https://www.soundandvision.com/content/trinnov-audio-altitude16-surround-sound-processor-review
- Home Cinema Choice, Trinnov Altitude16: https://www.homecinemachoice.com/node/121237
- Dirac Live Bass Control: https://www.dirac.com/live/bass-control/
- Dirac Live Processor for PC and Mac: https://www.dirac.com/products/computer-audio
- Archimago, Acourate v3.1: https://archimago.blogspot.com/2024/08/audiovero-acourate-v31-room-correction.html?m=0
- Dirac vs Acourate vs Audiolense forum thread: https://whatsbestforum.com/goto/post?id=280882
- Roon community, REW and rePhase convolution guide: https://community.roonlabs.com/t/a-guide-to-advanced-room-correction-with-rew-and-rephase-using-convolution-filters/90990
- Digital room correction (Wikipedia): https://en.wikipedia.org/wiki/Digital_room_correction
- Bharitkar, Hilmes, Kyriakakis, spatial averaging robustness (2002): https://ict.usc.edu/pubs/Robustness%20of%20Spatial%20Averaging%20Equalization%20Methods-%20A%20Statistical%20Approach.pdf
- StereoNET, CamillaDSP usage thread: https://www.stereonet.com/forums/topic/586299-camilladsp-how-are-you-using-it/
- SnakeOil forum, CamillaDSP for room correction: https://forums.snakeoil-os.net/Thread-CamillaDSP-for-Room-Correction?pid=4627
- diyAudio, sample-rate switcher for CamillaDSP (page with 4.1.0 report): https://www.diyaudio.com/community/goto/post?id=8317052
- diyAudio, multi-DAC clock and Dante discussion (May 2026): https://www.diyaudio.com/community/posts/8290136/
- AV Nirvana, wireless sub latency: https://www.avnirvana.com/posts/116337
- miniDSP forum, wired plus wireless sub: https://www.minidsp.com/community/threads/flex-in-2-2-w-1-wired-1-wireless-sub.23712/latest
- Arendal, subwoofer delay in REW: https://helpcenter.arendalsound.com/hc/en-us/articles/41926339309073-Impulse-Response-Delay-Measurements-in-REW-Why-Subwoofers-Can-Show-Large-Delays
- PipeWire devices man page: https://manpages.opensuse.org/Leap-15.6/pipewire/pipewire-devices.7.en.html
- PipeWire 1.6 (Phoronix): https://phoronix.com/news/PipeWire-1.6
- PipeWire NEWS (1.6.x): https://codegraph.jelmer.uk/pipewire/1.6.6-1/NEWS

Upmixing
- PAEDB, DAFx26 paper 14: https://www.dafx.de/paper-archive/2026/papers/DAFx26_paper_14.pdf
- S2X-Net, IEEE TASLP Oct 2026 (listing): https://signalprocessingsociety.org/publications-resources/ieee-transactions-audio-speech-and-language-processing/2026/10/s2x-net-stereo-multichannel-neural-upmixing-network
- SotF upmixer plugin docs: https://sotf.spinorama.org/reference/plugins/upmixer/
- FFmpeg `af_surround` upmix patch (2017): https://ffmpeg.org/pipermail/ffmpeg-cvslog/2017-June/107646.html (search listing, not read in full)

Video
- mpv issue 12425 (DV profile 7 / FEL): https://github.com/mpv-player/mpv/issues/12425
- mpv wiki, GPU Next vs GPU (mirror): https://github-wiki-see.page/m/mpv-player/mpv/wiki/GPU-Next-vs-GPU
- libplacebo README mirror: https://gitee.com/txgl/libplacebo
- libplacebo v7.360.0 on a release aggregator: https://newreleases.io/project/github/haasn/libplacebo/release/v7.360.0
- Beyond Audio on madVR Envy (retailer, 2026): https://www.beyondaudio.com/madvr-envy-changed-home-cinema-2026/
- DisplayCAL forum, 3D LUT for projector tone mapping (2021): https://hub.displaycal.net/forums/topic/3dlut-for-projector-tone-mapping/

The subject
- SDHT repository (public): https://github.com/praveenchandrahas/Software-Defined-Home-Theatre
