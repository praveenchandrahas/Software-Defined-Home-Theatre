#!/usr/bin/env bash
# Checks that the version is the same everywhere before anything is built or published:
# the git tag (if given), the VERSION file, the newest section of the changelog, and (if the repository has it) packaging/check-extra.sh.
#   check-version.sh [--repo DIR] [--tag vX.Y.Z]
set -euo pipefail
REPO=.; TAG=
while [ $# -gt 0 ]; do case "$1" in --repo) REPO=$2; shift 2 ;; --tag) TAG=$2; shift 2 ;; *) echo "unknown: $1" >&2; exit 2 ;; esac; done
REPO=$(cd "$REPO" && pwd)
CHANGELOG_FILE=CHANGELOG.md
REPO_FOR_SOURCE=$REPO
# shellcheck disable=SC2034,SC1091
( REPO=$REPO_FOR_SOURCE; . "$REPO/packaging/deb.sh" 2>/dev/null; echo "${CHANGELOG_FILE:-CHANGELOG.md}" ) > /tmp/.cf.$$ 2>/dev/null || echo CHANGELOG.md > /tmp/.cf.$$
CHANGELOG_FILE=$(cat /tmp/.cf.$$); rm -f /tmp/.cf.$$
V=$(tr -d ' \n' < "$REPO/VERSION")
fail() { echo "VERSION CHECK FAILED: $*" >&2; exit 1; }
[[ $V =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "VERSION is '$V', want X.Y.Z"
if [ -n "$TAG" ]; then [ "$TAG" = "v$V" ] || fail "tag is $TAG but VERSION says $V"; fi
C=$(grep -m1 -E '^## \[[0-9]+\.[0-9]+\.[0-9]+\] - [0-9]{4}-[0-9]{2}-[0-9]{2}' "$REPO/$CHANGELOG_FILE" | sed -E 's/^## \[([0-9.]+)\].*/\1/') || true
[ -n "$C" ] || fail "$CHANGELOG_FILE has no '## [X.Y.Z] - YYYY-MM-DD' section"
[ "$C" = "$V" ] || fail "newest section of $CHANGELOG_FILE is $C but VERSION says $V"
if [ -f "$REPO/packaging/check-extra.sh" ]; then bash "$REPO/packaging/check-extra.sh" "$V" "$REPO" || fail "packaging/check-extra.sh"; fi
echo "version OK: $V${TAG:+ (tag $TAG)}; $CHANGELOG_FILE newest section $C"
