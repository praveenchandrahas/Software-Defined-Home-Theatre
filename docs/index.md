# Software-defined home theatre (Linux, Atmos 5.1.2)

![Software-Defined Home Theatre: the four parts of the project (mpv-object-audio, linux-theater-dsp, Roomtone, and the supporting utilities mpv-shelf and seekthumbs) around a 5.1.2 room. Illustrative artwork, not a photograph or a measurement.](img/cover.png)

**At a glance.** A Linux laptop decodes Dolby Atmos files live and renders the objects to a 5.1.2 speaker layout; a Logitech Z906 plus
two ceiling speakers play them, and a projector shows the picture on a DIY 107 inch screen. There is no AV receiver: CamillaDSP on the laptop does the
EQ, delays and trims, and the amplifiers only amplify.

**For:** people building a similar Linux Atmos setup, or checking how it was tuned. This is a build log with working scripts, not a packaged product.

**Needs:** Kubuntu 24.04, PipeWire, Omniphony, harletty-bridge, a patched mpv, CamillaDSP and a 7.1 USB interface — see [Install](installation.md).

**Status:** everything on this site was measured at one seat, in one room, with one microphone. See [Status and what's verified](status.md) before relying on any number. The analysis
code that produced the numbers was written with an AI assistant. It was checked against simulated rooms and REW exports and used on real recordings in the author's room, but it has not
been repeated by another person or a second tool — see [Authorship](https://github.com/praveenchandrahas/Software-Defined-Home-Theatre#authorship-and-licence) in the repository README.

Room: about 10 x 10 ft, light-controlled and acoustically treated, with no space behind the seat for rear speakers, so **5.1.2 is the
largest layout used here** (7.1.4 and 5.1.4 are deliberately not used).

## Credits

This project is mostly glue and measurement. The hard part, decoding and rendering Atmos objects live on Linux, is the
work of others, and everything here stands on it:

- **[Omniphony](https://github.com/mgth/Omniphony)** by mgth: the object renderer (VBAP to any speaker layout), Omniphony
  Studio and the OSC control layer. **[mpv-omniphony](https://github.com/mgth/mpv-omniphony)** is the mpv integration
  used here.
- **[harletty-bridge](https://github.com/harletty/harletty-bridge)** by harletty: the decoder plugin (TrueHD and E-AC-3
  Atmos objects; its repository also carries DTS and DTS:X input support) that feeds Omniphony its objects.
- **[truehdd](https://github.com/truehdd/truehdd)** by Rainbaby, the open-source TrueHD Atmos decoder that the `harletty` decoder
  (inside harletty-bridge) is a fork of, per harletty's README.
- Also used: [mpv](https://mpv.io), [libplacebo](https://code.videolan.org/videolan/libplacebo), [PipeWire](https://pipewire.org),
  [CamillaDSP](https://github.com/HEnquist/camilladsp), [Room EQ Wizard](https://www.roomeqwizard.com), and
  [Cavern](https://github.com/VoidXH/Cavern) (used for offline rendering before the live path existed).

## Where to go next

- **[The repositories](repos.md)** — the six-repo map, and each one's own docs site.
- **[Install](installation.md)** — the packaged `.deb` install, and what a from-source build needs.
- **[Architecture](architecture.md)** and **[Technical write-up](technical-writeup.md)** — how the signal actually flows, end to end.
- **[Status and what's verified](status.md)** — what's measured, what's still open.
- **[Troubleshooting](troubleshooting.md)**.

The full build log, every number and every graph, is in this repository's own `docs/` folder and its
[README](https://github.com/praveenchandrahas/Software-Defined-Home-Theatre) — this site reuses that content rather than duplicating it by hand.
