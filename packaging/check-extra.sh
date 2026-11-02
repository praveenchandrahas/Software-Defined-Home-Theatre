#!/usr/bin/env bash
# Extra version checks of the main repository (called by kit/check-version.sh): install.sh and versions.lock must name the same release as VERSION.
set -euo pipefail
V=$1; R=$2
grep -q "^RELEASE=v$V\b" "$R/install.sh" || { echo "install.sh RELEASE is not v$V" >&2; exit 1; }
grep -q "^sdht_version=$V\$" "$R/versions.lock" || { echo "versions.lock sdht_version is not $V" >&2; exit 1; }
awk -F'\t' '$1=="deb" && $5=="PENDING" { bad=1 } END { exit !bad }' "$R/versions.lock" && { echo "versions.lock still has PENDING checksums: run packaging/kit/update-lock.sh after the component releases exist" >&2; exit 1; }
n=$(grep -c '^deb' "$R/versions.lock" || true)
[ "$n" -ge 5 ] || { echo "versions.lock lists only $n components (want 5: run packaging/kit/update-lock.sh after the component releases exist)" >&2; exit 1; }
echo "install.sh and versions.lock agree with $V ($n components)"
