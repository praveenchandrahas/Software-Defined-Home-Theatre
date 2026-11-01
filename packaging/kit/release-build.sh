#!/usr/bin/env bash
# Builds the release files TWICE (different temp folders, different build order) and fails if any byte differs, then writes the source tarball and
# SHA256SUMS into OUT.   release-build.sh [--repo DIR] --out DIR [--extra-file FILE ...]
# OUT gets: <pkg>_<version>_all.deb, <name>-<version>-source.tar.gz (git archive, fixed times), any --extra-file, and SHA256SUMS.
set -euo pipefail
KIT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=.; OUT=; EXTRA=()
while [ $# -gt 0 ]; do case "$1" in --repo) REPO=$2; shift 2 ;; --out) OUT=$2; shift 2 ;; --extra-file) EXTRA+=("$2"); shift 2 ;; *) echo "unknown: $1" >&2; exit 2 ;; esac; done
[ -n "$OUT" ] || { echo "need --out" >&2; exit 2; }
REPO=$(cd "$REPO" && pwd); mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
V=$(tr -d ' \n' < "$REPO/VERSION")
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git -C "$REPO" log -1 --format=%ct)}
A=$(mktemp -d); B=$(mktemp -d /var/tmp/sdht-b.XXXXXX); trap 'rm -rf "$A" "$B"' EXIT
echo "== build 1 (SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH)"
TMPDIR=$A "$KIT/build-deb.sh" --repo "$REPO" --out "$A/out" | tail -1
echo "== build 2 (other temp folder, other umask and locale)"
( umask 077; LANG=C.UTF-8 TMPDIR=$B "$KIT/build-deb.sh" --repo "$REPO" --out "$B/out" | tail -1 )
( cd "$A/out" && sha256sum -- * ) > "$A/sums"; ( cd "$B/out" && sha256sum -- * ) > "$B/sums"
if ! diff -u "$A/sums" "$B/sums"; then echo "NOT REPRODUCIBLE: the two builds differ" >&2; exit 1; fi
echo "reproducible: both builds are byte-identical"
cp "$A/out"/* "$OUT/"
NAME=$(basename "$REPO")
case "$NAME" in [Ss]oftware-Defined-Home-Theatre) NAME=sdht ;; esac
TB=$OUT/$NAME-$V-source.tar.gz
git -C "$REPO" archive --format=tar --prefix="$NAME-$V/" HEAD | gzip -9n > "$TB"
for f in "${EXTRA[@]}"; do cp "$f" "$OUT/"; done
( cd "$OUT" && find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%f\n' | LC_ALL=C sort | xargs -d '\n' sha256sum -- > SHA256SUMS )
cat "$OUT/SHA256SUMS"
