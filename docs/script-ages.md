# How old is each script?

Question from the README: which scripts, if any, predate the working sessions of 2026-10-20 to 24 in which most of the code was written with Claude? Checked on 2026-10-27 by five read-only reviews (one per repository, the two small ones together) from git history, file contents, the docs and what could be found of the earlier chats.

## Answer

**No code file in any of the seven repositories can be shown to be older than 2026-10-20.** What can be said:

- **Three early scripts were already in the working folder when the 2026-10-20 sessions started** (`set-eq.py` and `route-mpv.sh` as short first versions, `tone-test.sh` as a 1,020-byte script that is byte-identical to the committed one). The committed `set-eq.py` and `route-mpv.sh` are large rewrites of those first versions; whether any lines survive was not measured. The loop inside `tone-test.sh` first appears typed by hand in the chat of 2026-10-20 at about 10:58 IST, so it was written that morning at the earliest. The first `set-eq.py` was built from the REW export of 2026-10-19.
- **The `mpv-atmos` wrapper's option block is older than October**, by the repository's own account: its header says "as built in Sep 2026", and the repository copy is documented as newer than the copy installed on the laptop. Who wrote the original option block cannot be settled from the repositories. What is dated in git: `eq ensure` (2026-10-23) and `eq prepare` plus the IPC socket (2026-10-24) were added by Claude. `mpv-atmos-overlay-off.lua` is probably older as well, without a date.
- **Most of the code is from 2026-10-20 to 24**: the router and installers (10-21), the CamillaDSP generator (10-20 onwards), the delay, bed and recording kits (10-21), the sweep, sub (with the rattle detector), dialogue (STI), reflection and bar analysers (10-23), the drift tracker and the upmix code and tests (10-24).
- **Some code is from after that window**, so "mainly 2026-10-20 to 24" is too narrow now: the microphone calibration code, autocal, the status page and the overlay (10-26), seekthumbs (from 10-25; its web page 10-27), mpv-shelf (10-26), `resource-log` (10-27), the helper scripts `clone-all.sh`, `test-all.sh` and `check-installed.sh`, and the CI jobs.

## What this does not settle

- Git cannot see earlier work. The sdht history starts on 2026-10-21 with one commit that imported 46 files from a working folder, and the split repositories begin on 2026-10-25 and 26, so a commit date is only a latest-possible date.
- Only one earlier chat could be found by search, and nothing before 2026-10-20, so the July to September conversations were not checked.
- The wrapper installed on the laptop (`~/.local/bin/mpv-atmos`, 1,611 bytes, modified 2026-10-26 11:20 IST) has the same size as the repository copy, so it is most likely that copy installed on 10-26; its date says nothing about the original. The undated overlay Lua and anything in `~/HomeTheatre` were not checked. The seekthumbs README also mentions an earlier pre-generation script and a WebDAV browser script, neither of which is in any repository; whether they are ancestors of the current code is unknown.
- Style says nothing about age, and none was used.

## Other findings

- No vendored or third-party code and no licence headers were found in Roomtone, seekthumbs or mpv-shelf. The seekthumbs viewer `thumbfast.lua` is a protocol-compatible replacement, not a copy of thumbfast; it was not diffed against upstream.
- Standard formulas are re-implemented without citation in the code (the RBJ biquad cookbook, the IEC 60268-16 STI weights, Schroeder integration and the BS.1116 criterion). They are common published methods, not copied code.
- The microphone calibration file and the REW exports are supplied by the owner, not written by Claude.
