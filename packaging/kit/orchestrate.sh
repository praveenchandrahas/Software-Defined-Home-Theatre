#!/usr/bin/env bash
# Main-repo release orchestration: checks that every component release named in versions.lock exists and that its .deb matches the pinned sha256
# (and the component's own SHA256SUMS), builds the sdht meta package from the lock (twice, byte-identical), and assembles OUT with
# the component .debs, sdht, install.sh, versions.lock, the source tarball and one SHA256SUMS.   orchestrate.sh [--repo DIR] --out DIR [--local-debs DIR]
# --local-debs DIR takes the component .debs from DIR instead of from their releases (dry runs before the components are released); the pinned
# sha256 must still match, so it only works with the very same bytes.
set -euo pipefail
KIT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=.; OUT=; LOCAL=
while [ $# -gt 0 ]; do case "$1" in --repo) REPO=$2; shift 2 ;; --out) OUT=$2; shift 2 ;; --local-debs) LOCAL=$2; shift 2 ;; *) echo "unknown: $1" >&2; exit 2 ;; esac; done
[ -n "$OUT" ] || { echo "need --out" >&2; exit 2; }
REPO=$(cd "$REPO" && pwd); mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
LOCK=$REPO/versions.lock
D=$(mktemp -d); trap 'rm -rf "$D"' EXIT
n=0
while IFS=$'\t' read -r kind name ver file sha r; do
  [ "$kind" = deb ] || continue
  n=$((n + 1))
  if [ -n "$LOCAL" ]; then cp "$LOCAL/$file" "$D/$file"
  else
    mkdir -p "$D/rel-$r"
    gh release view "v$ver" --repo "praveenchandrahas/$r" >/dev/null || { echo "ORCHESTRATE FAIL: release v$ver of $r does not exist" >&2; exit 1; }
    gh release download "v$ver" --repo "praveenchandrahas/$r" --dir "$D/rel-$r" --pattern "$file" --pattern SHA256SUMS
    ( cd "$D/rel-$r" && sha256sum -c --ignore-missing SHA256SUMS >/dev/null ) || { echo "ORCHESTRATE FAIL: $r's own SHA256SUMS does not match its $file" >&2; exit 1; }
    cp "$D/rel-$r/$file" "$D/$file"
  fi
  got=$(sha256sum "$D/$file" | cut -d' ' -f1)
  [ "$got" = "$sha" ] || { echo "ORCHESTRATE FAIL: $file is $got but versions.lock pins $sha" >&2; exit 1; }
  echo "ok  $name $ver  $file  $sha"
done < "$LOCK"
[ "$n" -gt 0 ] || { echo "versions.lock lists no components" >&2; exit 1; }
extra=()
for f in "$D"/*_all.deb; do extra+=(--extra-file "$f"); done
"$KIT/release-build.sh" --repo "$REPO" --out "$OUT" "${extra[@]}" --extra-file "$REPO/install.sh" --extra-file "$LOCK"
