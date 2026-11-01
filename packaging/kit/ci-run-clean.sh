#!/usr/bin/env bash
# Starts ci-install-test.sh in a clean ubuntu:24.04: a Docker container (CI) or, with --chroot BASEDIR, a throw-away copy of a debootstrap
# tree (the sandbox without a Docker daemon; needs root).
#   ci-run-clean.sh [--chroot BASEDIR] --repo DIR --debs DIR [--smoke REL_PATH_IN_REPO [ARG]] -- DEB_FILENAME...
set -euo pipefail
KIT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CHROOT=; REPO=; DEBDIR=; SMOKE=; SMOKE_ARG=
while [ $# -gt 0 ]; do
  case "$1" in
    --chroot) CHROOT=$2; shift 2 ;;
    --repo) REPO=$(cd "$2" && pwd); shift 2 ;;
    --debs) DEBDIR=$(cd "$2" && pwd); shift 2 ;;
    --smoke) SMOKE=$2; shift 2; if [ "${1:-}" != "--" ] && [ $# -gt 0 ]; then SMOKE_ARG=$1; shift; fi ;;
    --) shift; break ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done
if [ -z "$REPO" ] || [ -z "$DEBDIR" ] || [ $# -eq 0 ]; then echo "usage: see the header of this script" >&2; exit 2; fi
inner=(bash /kit/ci-install-test.sh)
for d in "$@"; do inner+=(--deb "/debs/$d"); done
[ -n "$SMOKE" ] && inner+=(--smoke "/repo/$SMOKE" ${SMOKE_ARG:+"$SMOKE_ARG"})
if [ -z "$CHROOT" ]; then
  exec docker run --rm -v "$KIT:/kit:ro" -v "$REPO:/repo:ro" -v "$DEBDIR:/debs:ro" ubuntu:24.04 "${inner[@]}"
fi
[ "$(id -u)" = 0 ] || { echo "--chroot needs root" >&2; exit 1; }
T=$(mktemp -d /var/tmp/sdht-chroot.XXXXXX)
cleanup() { for m in dev/pts proc dev kit repo debs; do umount -l "$T/$m" 2>/dev/null || true; done; rm -rf "$T"; }
trap cleanup EXIT
cp -a "$CHROOT/." "$T/"
mkdir -p "$T/kit" "$T/repo" "$T/debs" "$T/proc" "$T/dev"
mount --bind "$KIT" "$T/kit"; mount --bind "$REPO" "$T/repo"; mount --bind "$DEBDIR" "$T/debs"
mount -t proc proc "$T/proc" 2>/dev/null || true
mount --bind /dev "$T/dev"; mount -t devpts devpts "$T/dev/pts" 2>/dev/null || true
cp /etc/resolv.conf "$T/etc/resolv.conf" 2>/dev/null || true
for v in http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY; do [ -n "${!v:-}" ] && printf 'export %s=%q\n' "$v" "${!v}" >> "$T/etc/profile.d/proxy-test.sh"; done
chroot "$T" env -i HOME=/root PATH=/usr/sbin:/usr/bin:/sbin:/bin ${http_proxy:+http_proxy=$http_proxy} ${https_proxy:+https_proxy=$https_proxy} "${inner[@]}"
