#!/usr/bin/env bash
# Gets the .deb files this repository's package depends on, listed in packaging/deps.txt as "<repo> <tag>" lines.
#   fetch-deps.sh --repo DIR --out DIR --mode main|release
# main:    clones each dependency's main branch (public, read-only) into OUT/src/<repo> and builds its .deb with the kit (used by CI)
# release: downloads the .deb of the dependency's release <tag> and checks it against that release's SHA256SUMS (used when verifying a release)
# OUT receives the .deb files; OUT/src holds the clones. Does nothing when there is no deps.txt.
set -euo pipefail
KIT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=.; OUT=; MODE=main
while [ $# -gt 0 ]; do case "$1" in --repo) REPO=$2; shift 2 ;; --out) OUT=$2; shift 2 ;; --mode) MODE=$2; shift 2 ;; *) echo "unknown: $1" >&2; exit 2 ;; esac; done
[ -n "$OUT" ] || { echo "need --out" >&2; exit 2; }
mkdir -p "$OUT/src"; OUT=$(cd "$OUT" && pwd)
[ -f "$REPO/packaging/deps.txt" ] || { echo "no packaging/deps.txt: no dependencies"; exit 0; }
while read -r dep tag _; do
  case "$dep" in ''|'#'*) continue ;; esac
  if [ "$MODE" = main ]; then
    git clone --quiet --depth 1 "https://github.com/praveenchandrahas/$dep" "$OUT/src/$dep"
    "$KIT/build-deb.sh" --repo "$OUT/src/$dep" --out "$OUT" | tail -1
  else
    d=$(mktemp -d)
    gh release download "$tag" --repo "praveenchandrahas/$dep" --dir "$d"
    ( cd "$d" && sha256sum -c --ignore-missing SHA256SUMS )
    cp "$d"/*_all.deb "$OUT/"
    rm -rf "$d"
    echo "release $tag of $dep: downloaded and verified"
  fi
done < "$REPO/packaging/deps.txt"
ls "$OUT"/*.deb
