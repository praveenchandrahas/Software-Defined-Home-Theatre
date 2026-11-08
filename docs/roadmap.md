# Roadmap

Ordered by payoff for effort. Nothing here is required for the system to work.

| Item | Why | Needs |
|------|-----|-------|
| Verify and document the auto-router on the real machine | Everything else depends on it | Reboot test, `eq status` output, journal excerpt |
| Make-up gain for EQ on | EQ on is quieter than off; fairer A/B | A few dB of Gain in CamillaDSP, checked on a loud scene for clipping |
| **Next:** centre channel, dialogue anchoring | Dialogue is most of what is watched; centre trim and speech-band response are unmeasured | Centre sweep export, a few dialogue-heavy scenes |
| **Next:** height channels | Apply the measured height delays, level and tone match to the bed, plus a high-pass | A/B against `--align=bed` |
| Height high-pass (about 100-120 Hz) | Small drivers, no sub, protect against loud low-frequency objects | A filter on channels 2 and 3, then height alignment with `--align` |
| Centre trim | Dialogue anchoring, if it bothers | Centre sweep export, listening |
| Tone matching of the five bed speakers | SL is brighter than FL (about +3 dB mids, +6 dB at 4-8 kHz before trims) | REW sweeps of FL FR FC SL SR at the final seat position, exported as text |
| Reference level | Know what knob position equals film level | Mic + test tone at a fixed Z906 position |
| Dynamic loudness / volume in CamillaDSP (undecided, not a night mode) | Quiet listening without losing bass | CamillaDSP Loudness filter docs; keep Z906 at the fixed reference |
| CamillaDSP GUI | Visual editing | Decide how it coexists with `set-eq.py` (it writes its own config) |
| Move to the planned desktop PC | More headroom, same software | Re-check interface names, channel order, re-run `tests/run.sh` |
| Run Spatial-Lab on the rig | It has only run in simulation: first real sound, the channel map by its Identify mode, Direct against Through | Vantec connected; correct USB sink name in its layout file; ceiling raised in steps from -40 dBFS; measured surround and height distances |
| Spatial-Lab: check by microphone, and optionally against Omniphony's own object test | Its image directions are predictions; the author deferred mic verification | Roomtone's mic and analysers; Omniphony's OSC `object_test` for the A/B |
| Spatial-Lab and Roomtone share one layout file | Two layout files must be kept in step by hand | Decide which format wins (Roomtone's `layout.yml` has the GUI) |
| Documentation for the next room | A larger room later would be a clean second build | This repo as the template |

Deliberately not planned: a night or low-volume preset (late-night viewing moves to the family TV and soundbar, see D13), rear or extra height speakers in the current room (see D1), multi-seat averaging (tuned for one seat).
