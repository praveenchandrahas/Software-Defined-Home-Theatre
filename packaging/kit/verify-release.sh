#!/usr/bin/env bash
# Downloads the assets of a PUBLISHED release and verifies them against its SHA256SUMS.   verify-release.sh OWNER/REPO TAG DIR
# Needs the gh CLI (GH_TOKEN in CI). Exits non-zero if a file is missing from SHA256SUMS or does not match.
set -euo pipefail
R=$1; T=$2; D=$3
mkdir -p "$D"
gh release download "$T" --repo "$R" --dir "$D" --clobber
cd "$D"
[ -f SHA256SUMS ] || { echo "release has no SHA256SUMS" >&2; exit 1; }
sha256sum -c SHA256SUMS
for f in *; do [ "$f" = SHA256SUMS ] && continue; grep -q "  $f\$" SHA256SUMS || { echo "$f is not covered by SHA256SUMS" >&2; exit 1; }; done
echo "release $T of $R: all $(grep -c . SHA256SUMS) files match SHA256SUMS"
