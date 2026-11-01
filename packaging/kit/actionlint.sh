#!/usr/bin/env bash
# Downloads actionlint 1.7.9 from its GitHub release (the sha256 below is checked, from the release's own checksums file) and lints every workflow.
#   actionlint.sh [--repo DIR]
set -euo pipefail
VER=1.7.9
SHA=233b280d05e100837f4af1433c7b40a5dcb306e3aa68fb4f17f8a7f45a7df7b4   # actionlint_1.7.9_linux_amd64.tar.gz
REPO=.; [ "${1:-}" = --repo ] && REPO=$2
CACHE=${XDG_CACHE_HOME:-${TMPDIR:-/tmp}}/sdht-actionlint-$VER
if [ ! -x "$CACHE/actionlint" ]; then
  mkdir -p "$CACHE"
  curl -fsSL --proto '=https' -o "$CACHE/a.tgz" "https://github.com/rhysd/actionlint/releases/download/v$VER/actionlint_${VER}_linux_amd64.tar.gz"
  echo "$SHA  $CACHE/a.tgz" | sha256sum -c - >/dev/null || { echo "actionlint download does not match the pinned sha256" >&2; rm -f "$CACHE/a.tgz"; exit 1; }
  tar -xzf "$CACHE/a.tgz" -C "$CACHE" actionlint
fi
cd "$REPO"
"$CACHE/actionlint" -color
echo "actionlint OK ($("$CACHE/actionlint" -version | head -1))"
