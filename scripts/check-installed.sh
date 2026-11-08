#!/usr/bin/env bash
# Compares what is INSTALLED on this machine with the copies in the repositories. READ-ONLY:
#   - it only reads files (cmp, readlink, git status); it writes nothing, installs nothing, deletes nothing, uses no network and no sudo;
#   - when something differs it PRINTS the command you would run to update it. You decide whether to run it.
# Usage:  scripts/check-installed.sh [--diff]        --diff also shows the differences
# Exit status: 0 = everything identical, 1 = something differs or is missing.
# Folders: the repositories side by side (SDHT_WORKSPACE overrides), installed scripts in BIN (default ~/.local/bin), mpv config in MPVCONF.
HERE=$(cd "$(dirname "$0")/.." && pwd)
WS="${SDHT_WORKSPACE:-$(dirname "$HERE")}"
RT=roomtone; [ -d "$WS/roomtone" ] || [ ! -d "$WS/theater-measurement" ] || RT=theater-measurement   # the folder is called theater-measurement until you rename it
BIN="${BIN:-$HOME/.local/bin}"
MPVCONF="${MPVCONF:-$HOME/.config/mpv-object-audio}"
SHOWDIFF=0; [ "${1:-}" = "--diff" ] && SHOWDIFF=1
bad=0; n=0
row() {   # row LABEL INSTALLED REPOFILE UPDATE-HINT
  local label=$1 inst=$2 repo=$3 hint=$4
  n=$((n + 1))
  if [ ! -f "$repo" ]; then printf '%-24s NO-REPO   (repository file not found: %s)\n' "$label" "$repo"; bad=1; return; fi
  if [ ! -e "$inst" ]; then printf '%-24s MISSING    (not installed: %s)\n             to install: %s\n' "$label" "$inst" "$hint"; bad=1; return; fi
  if cmp -s "$inst" "$repo"; then printf '%-24s identical\n' "$label"
  else
    # comments and blank lines only? (a leading "#!" line is behaviour and counts)
    local note=""
    if diff -q <(grep -v -E '^[[:space:]]*(#[^!].*)?$' "$inst") <(grep -v -E '^[[:space:]]*(#[^!].*)?$' "$repo") >/dev/null 2>&1; then
      note="  comments/blank lines only, no difference in behaviour"
    fi
    printf '%-24s DIFFERS    (%s)%s\n             to update: %s\n' "$label" "$inst" "$note" "$hint"; bad=1
    if [ "$SHOWDIFF" = 1 ]; then
      local d total; d=$(diff -u "$inst" "$repo"); total=$(printf '%s\n' "$d" | wc -l)
      printf '%s\n' "$d" | head -40 | sed 's/^/             | /'
      [ "$total" -gt 40 ] && printf '             | ... %d more diff line(s) not shown; see them all with:  diff -u %s %s\n' "$((total - 40))" "$inst" "$repo"
    fi
  fi
}
R="$WS/linux-theater-dsp/scripts"; M="$WS/mpv-object-audio/scripts"
UP="cd $WS/linux-theater-dsp && ./scripts/install-autoroute.sh"
row theater-route        "$BIN/theater-route"      "$R/theater-route"      "$UP"
row set-eq.py            "$BIN/set-eq.py"          "$R/set-eq.py"          "$UP"
row upmix.py             "$BIN/upmix.py"           "$R/upmix.py"           "$UP"
row upmix_engine.py      "$BIN/upmix_engine.py"    "$R/upmix_engine.py"    "$UP"
row mpv-object-audio     "$BIN/mpv-object-audio"   "$M/mpv-object-audio"   "install -m 755 $M/mpv-object-audio $BIN/mpv-object-audio   (just the wrapper; cd $WS/mpv-object-audio && ./scripts/object-audio-install.sh also updates the engine, bridges and menus)"
row mpv-atmos            "$BIN/mpv-atmos"          "$M/mpv-atmos"          "install -m 755 $M/mpv-atmos $BIN/mpv-atmos   (this wrapper is hand-installed; compare it first with --diff)"
if [ -e "$BIN/eq" ]; then
  n=$((n + 1)); if [ "$(readlink "$BIN/eq" 2>/dev/null)" = "theater-route" ]; then printf '%-24s identical    (symlink to theater-route)\n' "eq"; else printf '%-24s DIFFERS    (not a symlink to theater-route)\n' "eq"; bad=1; fi
fi
[ -f "$WS/seekthumbs/thumbfast.lua" ] && [ -e "$MPVCONF/scripts/thumbfast.lua" ] && row "seekthumbs viewer" "$MPVCONF/scripts/thumbfast.lua" "$WS/seekthumbs/thumbfast.lua" "cd $WS/seekthumbs && ./seekthumbs.py install-viewer"
# optional parts: only checked once they are installed
for c in "$MPVCONF" "$HOME/.config/mpv"; do
  [ -f "$WS/mpv-shelf/shelf.lua" ] && [ -e "$c/scripts/shelf.lua" ] && row "mpv-shelf script" "$c/scripts/shelf.lua" "$WS/mpv-shelf/shelf.lua" "cd $WS/mpv-shelf && ./install-shelf.sh"
done
[ -f "$WS/mpv-shelf/shelf-index" ] && [ -e "$BIN/shelf-index" ] && row "shelf-index" "$BIN/shelf-index" "$WS/mpv-shelf/shelf-index" "cd $WS/mpv-shelf && ./install-shelf.sh"
if [ -e "$BIN/theater-ctld" ]; then
  row theater-ctld      "$BIN/theater-ctld"                         "$WS/$RT/gui/theater-ctld"                          "cd $WS/$RT/gui && ./install-ctld.sh"
  row "ctld web page"   "$HOME/.local/share/theater-ctld/index.html" "$WS/$RT/gui/index.html"    "cd $WS/$RT/gui && ./install-ctld.sh"
  if command -v systemctl >/dev/null 2>&1; then              # does the page start with the system? (read-only: only asks systemd)
    n=$((n + 1)); en=$(systemctl --user is-enabled theater-ctld.service 2>/dev/null)
    if [ "$en" = enabled ]; then printf '%-24s enabled (starts with your desktop session)\n' "ctld autostart"
    else printf '%-24s NOT ENABLED (%s)\n             to enable: systemctl --user enable --now theater-ctld.service\n' "ctld autostart" "${en:-unknown}"; bad=1; fi
    lg=$(loginctl show-user "${USER:-$(id -un)}" -p Linger --value 2>/dev/null)
    [ "$lg" = no ] && printf '%-24s linger is off: services start when you log in to the desktop; for boot without a login: loginctl enable-linger %s\n' "" "${USER:-$(id -un)}"
  fi
fi
for c in "$MPVCONF" "$HOME/.config/mpv"; do
  [ -e "$c/scripts/theater_status.lua" ] && row "mpv status overlay" "$c/scripts/theater_status.lua" "$WS/$RT/overlay/theater_status.lua" "cd $WS/$RT/overlay && ./install-theater-status.sh --bindings"
done
echo
echo "repository state (local only, no network):"
for r in UMBRELLA linux-theater-dsp mpv-object-audio seekthumbs mpv-shelf $RT spatial-lab; do
  d="$WS/$r"; [ "$r" = UMBRELLA ] && d="$HERE"
  if [ -d "$d/.git" ]; then
    dirty=$(git -C "$d" status --porcelain 2>/dev/null | wc -l)
    printf '  %-20s %s  %s%s\n' "$([ "$r" = UMBRELLA ] && basename "$HERE" || echo "$r")" "$(git -C "$d" log -1 --format='%h %cs' 2>/dev/null)" "$([ "$dirty" -gt 0 ] && echo "$dirty uncommitted change(s)" || echo clean)" "$(git -C "$d" status -sb 2>/dev/null | head -1 | grep -oE '\[(ahead|behind)[^]]*\]' | sed 's/^/  /')"
  else
    printf '  %-20s not found in %s\n' "$r" "$WS"
  fi
done
echo
if [ "$bad" = 0 ]; then echo "OK: $n item(s) checked, everything installed matches the repositories."; else echo "ATTENTION: something differs or is missing (see above). Nothing was changed."; fi
exit $bad
