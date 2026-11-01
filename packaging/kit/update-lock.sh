#!/usr/bin/env bash
# Rewrites versions.lock from the component RELEASES: for each "repo=tag" argument it downloads the release's .deb, checks it against that
# release's own SHA256SUMS, and records its version and sha256. The CamillaDSP line and sdht_version are kept as they are.
#   update-lock.sh [--repo DIR] linux-theater-dsp=v0.1.0 Roomtone=v0.1.0 seekthumbs=v0.1.0 mpv-shelf=v0.1.0 mpv-object-audio=v0.1.0
# Needs the gh CLI.
set -euo pipefail
REPO=.
[ "${1:-}" = --repo ] && { REPO=$2; shift 2; }
LOCK=$REPO/versions.lock
D=$(mktemp -d); trap 'rm -rf "$D"' EXIT
{ grep -E '^(#|sdht_version=)' "$LOCK"
  for spec in "$@"; do
    r=${spec%%=*}; t=${spec#*=}
    mkdir -p "$D/$r"
    gh release download "$t" --repo "praveenchandrahas/$r" --dir "$D/$r" --pattern '*_all.deb' --pattern SHA256SUMS
    ( cd "$D/$r" && sha256sum -c --ignore-missing SHA256SUMS >&2 )
    f=$(cd "$D/$r" && ls -- *_all.deb); name=${f%%_*}; ver=${f#*_}; ver=${ver%%_*}
    [ "v$ver" = "$t" ] || { echo "release $t of $r ships $f" >&2; exit 1; }
    printf 'deb\t%s\t%s\t%s\t%s\t%s\n' "$name" "$ver" "$f" "$(sha256sum "$D/$r/$f" | cut -d' ' -f1)" "$r"
  done
  grep -E '^external' "$LOCK"
} > "$D/new"
mv "$D/new" "$LOCK"; cat "$LOCK"
