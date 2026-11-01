#!/usr/bin/env bash
# Builds one .deb (Architecture: all) from a repository checkout, reproducibly.
#
#   build-deb.sh [--repo DIR] [--out DIR] [--version X.Y.Z]
#
# The repository supplies packaging/deb.sh, which sets PKG, SUMMARY, DESCRIPTION, DEPENDS, RECOMMENDS, SUGGESTS, HOMEPAGE, PYDIRS and
# defines stage() to copy files into "$ROOT" (helpers below). VERSION comes from --version or the VERSION file (the release workflow
# checks that the git tag says the same). Same input, same bytes: file times are clamped to SOURCE_DATE_EPOCH (default: the commit time),
# owner is root:root, the file lists are sorted, the compression is fixed. See docs/release-process.md.
set -euo pipefail
umask 022
export LC_ALL=C TZ=UTC
KIT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=.; OUT=dist; VERSION=
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO=$2; shift 2 ;;
    --out) OUT=$2; shift 2 ;;
    --version) VERSION=$2; shift 2 ;;
    -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
REPO=$(cd "$REPO" && pwd)
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
[ -f "$REPO/packaging/deb.sh" ] || { echo "no $REPO/packaging/deb.sh" >&2; exit 1; }
[ -n "$VERSION" ] || VERSION=$(tr -d ' \n' < "$REPO/VERSION")
case "$VERSION" in [0-9]*.[0-9]*.[0-9]*) ;; *) echo "bad version '$VERSION' (want X.Y.Z)" >&2; exit 1 ;; esac
if [ -z "${SOURCE_DATE_EPOCH:-}" ]; then
  SOURCE_DATE_EPOCH=$(git -C "$REPO" log -1 --format=%ct 2>/dev/null) || SOURCE_DATE_EPOCH=
  [ -n "$SOURCE_DATE_EPOCH" ] || { echo "set SOURCE_DATE_EPOCH (not a git checkout)" >&2; exit 1; }
fi
export SOURCE_DATE_EPOCH

MAINTAINER="Praveen Chandrahas <308781499+praveenchandrahas@users.noreply.github.com>"
CHANGELOG_FILE=CHANGELOG.md; SECTION=sound; HOMEPAGE=; DEPENDS=; RECOMMENDS=; SUGGESTS=; PYDIRS=; SUMMARY=; DESCRIPTION=; PKG=
# shellcheck source=/dev/null
. "$REPO/packaging/deb.sh"
for v in PKG SUMMARY DESCRIPTION; do [ -n "${!v}" ] || { echo "packaging/deb.sh must set $v" >&2; exit 1; }; done

WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
ROOT=$WORK/root; mkdir -p "$ROOT/DEBIAN"
export REPO ROOT

# ---- helpers for stage()
inst()    { local mode=$1 src=$2 dst=$3; install -D -m "$mode" "$REPO/$src" "$ROOT$dst"; }          # inst 755 scripts/x /usr/lib/pkg/x
instdir() { local src=$1 dst=$2; mkdir -p "$ROOT$dst"; (cd "$REPO/$src" && find . -type f ! -name '__pycache__' ! -path '*/__pycache__/*' ! -name '*.pyc' -print0 | sort -z) |
            while IFS= read -r -d '' f; do local m=644; [ -x "$REPO/$src/$f" ] && m=755; install -D -m "$m" "$REPO/$src/$f" "$ROOT$dst/${f#./}"; done; }
link()    { mkdir -p "$(dirname "$ROOT$2")"; ln -s "$1" "$ROOT$2"; }                               # link TARGET /usr/bin/name
script()  { mkdir -p "$(dirname "$ROOT$1")"; cat > "$ROOT$1"; chmod 755 "$ROOT$1"; }               # script /usr/bin/name <<'X' ... X
pyshebang() { local f; for f in "$@"; do sed -i '1s|^#!/usr/bin/env python3|#!/usr/bin/python3|; 1s|^#!/usr/bin/env python$|#!/usr/bin/python3|' "$ROOT$f"; done; }
manpage() {   # manpage COMMAND "one-line description" [extra paragraph]  -> a minimal man page in section 1
  local cmd=$1 desc=$2 extra=${3:-} d="$ROOT/usr/share/man/man1"
  mkdir -p "$d"
  { printf '.TH %s 1 "" "%s %s" "User commands"\n' "$(echo "$cmd" | tr '[:lower:]' '[:upper:]')" "$PKG" "$VERSION"
    printf '.SH NAME\n%s \\- %s\n' "$cmd" "$desc"
    printf '.SH SYNOPSIS\n.B %s\n[options]\n' "$cmd"
    printf '.SH DESCRIPTION\n%s\n' "$desc."
    [ -n "$extra" ] && printf '.PP\n%s\n' "$extra"
    printf '.PP\nRun \\fB%s --help\\fR (or read /usr/share/doc/%s/README.md) for the options.\n' "$cmd" "$PKG"
    printf '.SH AUTHOR\nPraveen Chandrahas. Written with an AI assistant (Claude, Anthropic); see /usr/share/doc/%s/NOTICE.\n' "$PKG"
  } | gzip -9n > "$d/$cmd.1.gz"; chmod 644 "$d/$cmd.1.gz"; }
export -f inst instdir link script pyshebang manpage

stage "$ROOT"

# ---- documentation, licence, changelog
DOC=$ROOT/usr/share/doc/$PKG; mkdir -p "$DOC"
install -m 644 "$REPO/NOTICE" "$DOC/NOTICE"
install -m 644 "$REPO/LICENSE" "$DOC/LICENSE"
[ -f "$REPO/README.md" ] && install -m 644 "$REPO/README.md" "$DOC/README.md"
python3 "$KIT/changelog2deb.py" "$REPO/$CHANGELOG_FILE" "$PKG" "$VERSION" "$MAINTAINER" | gzip -9n > "$DOC/changelog.gz"
{
  echo "Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/"
  echo "Upstream-Name: $PKG"
  echo "Upstream-Contact: $MAINTAINER"
  echo "Source: ${HOMEPAGE:-https://github.com/praveenchandrahas/Software-Defined-Home-Theatre}"
  echo
  echo "Files: *"
  echo "Copyright: 2026 Praveen Chandrahas"
  echo "License: Apache-2.0"
  echo
  echo "License: Apache-2.0"
  echo " Licensed under the Apache License, Version 2.0. On Debian and Ubuntu systems the full"
  echo " text is in /usr/share/common-licenses/Apache-2.0; the same text is shipped with this"
  echo " package as /usr/share/doc/$PKG/LICENSE, and the project NOTICE as"
  echo " /usr/share/doc/$PKG/NOTICE."
} > "$DOC/copyright"
chmod 644 "$DOC/copyright"

# ---- maintainer scripts: only a cleanup of Python byte-code that root may have written next to the installed scripts. Nothing is
# enabled, started or written into any home folder, and no audio configuration is touched.
if [ -n "$PYDIRS" ]; then
  {
    echo '#!/bin/sh'
    echo 'set -e'
    echo 'case "$1" in remove|purge|upgrade|failed-upgrade|abort-install|abort-upgrade|disappear)'
    for d in $PYDIRS; do
      echo "  find $d -depth -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true"
    done
    echo '  ;; esac'
    echo 'exit 0'
  } > "$ROOT/DEBIAN/postrm"
  chmod 755 "$ROOT/DEBIAN/postrm"
fi

# ---- normalise: modes, times, md5sums, control
find "$ROOT" -type d -exec chmod 755 {} +
find "$ROOT" -mindepth 1 ! -path "$ROOT/DEBIAN" ! -path "$ROOT/DEBIAN/*" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
(cd "$ROOT" && find . -type f ! -path './DEBIAN/*' -print0 | sort -z | xargs -0 md5sum | sed 's|  \./|  |') > "$ROOT/DEBIAN/md5sums"
SIZE=$(du -sk --apparent-size --exclude=DEBIAN "$ROOT" | cut -f1)
{
  echo "Package: $PKG"
  echo "Version: $VERSION"
  echo "Architecture: all"
  echo "Maintainer: $MAINTAINER"
  echo "Installed-Size: $SIZE"
  [ -n "$DEPENDS" ] && echo "Depends: $DEPENDS"
  [ -n "$RECOMMENDS" ] && echo "Recommends: $RECOMMENDS"
  [ -n "$SUGGESTS" ] && echo "Suggests: $SUGGESTS"
  echo "Section: $SECTION"
  echo "Priority: optional"
  [ -n "$HOMEPAGE" ] && echo "Homepage: $HOMEPAGE"
  echo "Description: $SUMMARY"
  printf '%s\n' "$DESCRIPTION" | sed -e 's/^\.$//' | fmt -w 76 | sed -e 's/[[:space:]]*$//' -e 's/^$/./' -e 's/^/ /'
} > "$ROOT/DEBIAN/control"
chmod 644 "$ROOT/DEBIAN/control" "$ROOT/DEBIAN/md5sums"
touch -h -d "@$SOURCE_DATE_EPOCH" "$ROOT/DEBIAN" "$ROOT/DEBIAN"/*

DEB=$OUT/${PKG}_${VERSION}_all.deb
rm -f "$DEB"
dpkg-deb --root-owner-group -Zxz -z6 --build "$ROOT" "$DEB" >/dev/null
echo "$DEB"
sha256sum "$DEB" | sed 's|  .*/|  |'
