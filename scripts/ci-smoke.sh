#!/usr/bin/env bash
# Smoke test of the INSTALLED sdht meta package and the five components it pulls in: every command is on PATH and resolves to /usr/bin, the
# per-user setup runs as a dry run only, nothing is written to the (throw-away) home folder, and versions.lock matches what dpkg installed.
#   scripts/ci-smoke.sh
set -euo pipefail
H=$(mktemp -d); trap 'rm -rf "$H"' EXIT
export HOME=$H XDG_CONFIG_HOME=$H/.config
fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }
for c in sdht-setup theater-setup roomtone-setup seekthumbs-setup mpv-shelf-setup mpv-object-audio mpv-object-audio-install eq autocal theater-ctld seekthumbs shelf-index; do
  [ "$(command -v "$c")" = "/usr/bin/$c" ] || fail "$c resolves to '$(command -v "$c")'"
done
LOCK=/usr/share/doc/sdht/versions.lock
[ -f "$LOCK" ] || fail "versions.lock not installed"
while IFS=$'\t' read -r kind name ver _; do
  [ "$kind" = deb ] || continue
  [ "$(dpkg-query -W -f='${Version}' "$name")" = "$ver" ] || fail "$name is not at the locked version $ver"
  echo "ok  $name $ver"
done < "$LOCK"
echo "== setup commands, dry run"
sdht-setup --dry-run install | tee "$H/dry.txt"
grep -q 'would run: systemctl --user enable --now theater-router.service' "$H/dry.txt" || fail "router step missing from the dry run"
grep -q 'would run: systemctl --user enable --now theater-ctld.service' "$H/dry.txt" || fail "status page step missing from the dry run"
sdht-setup --dry-run uninstall >/dev/null
sdht-setup check | tail -12
[ -z "$(find "$H" -mindepth 1 -not -name dry.txt)" ] || { find "$H"; fail "something was written into the home folder"; }
echo "SMOKE OK (sdht)"
