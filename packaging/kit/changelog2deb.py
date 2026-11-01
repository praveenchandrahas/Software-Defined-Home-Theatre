#!/usr/bin/env python3
"""Turns CHANGELOG.md ("## [X.Y.Z] - YYYY-MM-DD" sections) into a Debian changelog on stdout. Usage: changelog2deb.py CHANGELOG.md PKG VERSION MAINTAINER
The newest entry must be VERSION (the release workflow checks the same thing). Dates are taken from the headings, so the output is reproducible."""
import datetime
import re
import sys
import textwrap

path, pkg, version, maint = sys.argv[1:5]
text = open(path, encoding="utf-8").read()
secs = re.split(r"(?m)^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})\s*$", text)
entries = [(secs[i], secs[i + 1], secs[i + 2]) for i in range(1, len(secs) - 2, 3)]
if not entries or entries[0][0] != version:
    sys.exit(f"CHANGELOG.md: the newest section is {entries[0][0] if entries else 'missing'}, expected {version}")
out = []
for ver, date, body in entries:
    d = datetime.date.fromisoformat(date)
    items = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s[:2] in ("- ", "* "):
            items.append(s[2:].strip())
        elif items:
            items[-1] += " " + s
        else:
            items.append(s)
    out.append(f"{pkg} ({ver}) unstable; urgency=low\n")
    for it in items or ["Release."]:
        out.append(textwrap.fill(it, width=78, initial_indent="  * ", subsequent_indent="    ", break_long_words=False, break_on_hyphens=False))
    out.append(f"\n -- {maint}  {d.strftime('%a')}, {d.day:02d} {d.strftime('%b %Y')} 00:00:00 +0000\n")
sys.stdout.write("\n".join(out))
