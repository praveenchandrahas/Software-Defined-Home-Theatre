#!/usr/bin/env bash
# Gets the component .debs named in versions.lock: from their releases when those exist, otherwise (CI before the first releases) builds them from
# the component's main branch with the kit.   fetch-components.sh [--repo DIR] --out DIR
set -euo pipefail
KIT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=.; OUT=
while [ $# -gt 0 ]; do case "$1" in --repo) REPO=$2; shift 2 ;; --out) OUT=$2; shift 2 ;; *) echo "unknown: $1" >&2; exit 2 ;; esac; done
[ -n "$OUT" ] || { echo "need --out" >&2; exit 2; }
mkdir -p "$OUT/src"; OUT=$(cd "$OUT" && pwd)
while IFS=$'\t' read -r kind name ver file _sha r; do
  [ "$kind" = deb ] || continue
  d=$(mktemp -d)
  if gh release download "v$ver" --repo "praveenchandrahas/$r" --dir "$d" --pattern "$file" --pattern SHA256SUMS 2>/dev/null; then
    ( cd "$d" && sha256sum -c --ignore-missing SHA256SUMS >/dev/null ) && cp "$d/$file" "$OUT/" && echo "release v$ver of $r: $file"
  else
    echo "no release v$ver of $r yet: building $name from its main branch"
    git clone --quiet --depth 1 "https://github.com/praveenchandrahas/$r" "$OUT/src/$r"
    "$KIT/build-deb.sh" --repo "$OUT/src/$r" --out "$OUT" | tail -1
  fi
  rm -rf "$d"
done < "$REPO/versions.lock"
ls "$OUT"/*.deb
