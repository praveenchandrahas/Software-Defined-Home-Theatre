#!/usr/bin/env bash
# Prints the release notes: the changelog section of this version plus the standing caveats.
#   release-notes.sh [--repo DIR] [--attest ok|skipped] [--extra FILE]
set -euo pipefail
REPO=.; ATT=skipped; EXTRA=
while [ $# -gt 0 ]; do case "$1" in --repo) REPO=$2; shift 2 ;; --attest) ATT=$2; shift 2 ;; --extra) EXTRA=$2; shift 2 ;; *) echo "unknown: $1" >&2; exit 2 ;; esac; done
REPO=$(cd "$REPO" && pwd)
V=$(tr -d ' \n' < "$REPO/VERSION")
CHANGELOG_FILE=$( (REPO=$REPO; . "$REPO/packaging/deb.sh" >/dev/null 2>&1; echo "${CHANGELOG_FILE:-CHANGELOG.md}") 2>/dev/null || echo CHANGELOG.md)
echo "**PRE-RELEASE $V. Experimental.** Read the caveats below before you install this."
echo
awk -v v="$V" '$0 ~ "^## \\[" v "\\]" {on=1; next} on && /^## \[/ {exit} on {print}' "$REPO/$CHANGELOG_FILE" | sed '/./,$!d'
[ -n "$EXTRA" ] && { echo; cat "$EXTRA"; }
cat <<'TXT'

## What this release is, and is not

- **Experimental, one author, one room.** Written with an AI assistant; checked against simulated rooms and REW exports; used and checked by the author in his own room (one room, one author). No external or second-person validation yet.
- **Unsigned.** The packages carry no GPG signature (there is no signing key in this pipeline). Integrity comes from `SHA256SUMS` and, where the line below says so, build-provenance attestations. A signed apt repository would need the author's own key.
- **What the automated checks prove.** CI proves that the packages build reproducibly from the tag, install on a clean Ubuntu 24.04, pass the repository's simulated tests and a smoke test run from the installed paths, and remove and purge cleanly. It does **not** prove that the software works on a real rig: the packaging itself has **not** been run on the author's rig, and the signal-processing code has only been used by the author in his own room.
- **Packaged and tested only in simulation and in a clean Ubuntu 24.04 environment in CI.** No audio hardware, PipeWire daemon or CamillaDSP was involved in those tests.
- Try it on a spare machine or a throw-away user first. Nothing here enables a service or edits a home folder until you run the matching `*-setup` command, and each has `--dry-run`.

## Verify what you download

```
sha256sum -c SHA256SUMS --ignore-missing
gh attestation verify FILE --repo praveenchandrahas/<this-repository>     # only if attestations were created
```
TXT
if [ "$ATT" = ok ]; then echo; echo "Build-provenance attestations were created for the files in SHA256SUMS."; else echo; echo "Build-provenance attestations could **not** be created for this release; use SHA256SUMS only."; fi
