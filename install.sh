#!/usr/bin/env bash
# install.sh: installs the packaged parts of the Software Defined Home Theatre on Ubuntu 24.04 (a pre-release; read docs/packaging.md first).
#
#   ./install.sh --dry-run          show what would happen; fetches only SHA256SUMS and versions.lock, installs and downloads nothing else
#   ./install.sh                    download the release, verify it, ask, then install
#   ./install.sh --yes              same without the questions (still shows the plan)
#   Options: --no-camilladsp  skip CamillaDSP     --camilla-dir DIR  where the camilladsp binary goes (default ~/.local/bin)
#            --release TAG    another release     --keep  keep the download folder       -h | --help
#
# What it does, in this order:
#   1. downloads SHA256SUMS and versions.lock of ONE release of this repository, and every file it later installs, from the same release
#   2. checks every downloaded file against SHA256SUMS (and versions.lock against SHA256SUMS); any mismatch stops it before anything is installed
#   3. asks, then runs ONE sudo command: apt-get install -y ./the-packages.deb (sudo is used for nothing else; skipped when you are root)
#   4. installs CamillaDSP from github.com/HEnquist/camilladsp (the version pinned in versions.lock) after checking the SHA256 pinned there;
#      it goes into your own folder, no sudo. CamillaDSP is not in Ubuntu's repositories.
#   5. checks, but never downloads, the player stack (Omniphony, harletty-bridge, mpv-omniphony: other people's software)
#   6. prints the next steps
# It does not enable or start services, edit your home folder's configuration, or touch PipeWire/CamillaDSP configuration. The packages'
# own `sdht-setup` does the per-user part later, with --dry-run.
# Recommended way to run it: download, read, verify, run (docs/packaging.md). Do not pipe it from curl into a shell.
set -euo pipefail

RELEASE=v0.1.0                                      # the release this copy of the script belongs to (the release workflow checks it against the tag)
REPO=praveenchandrahas/Software-Defined-Home-Theatre
BASE=${SDHT_BASE_URL:-https://github.com/$REPO/releases/download}
DOCS=https://github.com/$REPO/blob/main/docs

DRY=0; YES=0; CAMILLA=1; KEEP=0; CAMILLA_DIR=${HOME:-}/.local/bin
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run|-n) DRY=1 ;;
    --yes|-y) YES=1 ;;
    --no-camilladsp) CAMILLA=0 ;;
    --camilla-dir) shift; CAMILLA_DIR=${1:?--camilla-dir needs a folder} ;;
    --release) shift; RELEASE=${1:?--release needs a tag} ;;
    --keep) KEEP=1 ;;
    -h|--help) sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 2 ;;
  esac
  shift
done

say()  { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
die()  { printf 'install.sh: %s\n' "$*" >&2; exit 1; }
for t in curl sha256sum awk tar; do command -v "$t" >/dev/null 2>&1 || die "$t is required"; done

WORK=$(mktemp -d "${TMPDIR:-/tmp}/sdht-install.XXXXXX")
cleanup() { if [ "$KEEP" = 1 ]; then say "kept: $WORK"; else rm -rf "$WORK"; fi; }
trap cleanup EXIT

fetch() {   # fetch FILE URL: https only (or file:// for tests); no redirects to other schemes
  local out=$1 url=$2
  case "$url" in
    https://*) curl -fsSL --proto '=https' --tlsv1.2 --retry 2 -o "$out" "$url" || die "download failed: $url" ;;
    file://*)  curl -fsSL -o "$out" "$url" || die "copy failed: $url" ;;
    *) die "refusing to fetch a non-https address: $url" ;;
  esac
}
sum_of() { awk -v f="$1" '$2 == f { print $1 }' "$WORK/SHA256SUMS"; }
verify() {  # verify FILE: it must be listed in SHA256SUMS and match
  local f=$1 want got
  want=$(sum_of "$f"); [ -n "$want" ] || die "$f is not listed in SHA256SUMS"
  got=$(sha256sum "$WORK/$f" | awk '{print $1}')
  [ "$want" = "$got" ] || die "CHECKSUM MISMATCH for $f (SHA256SUMS says $want, the download is $got). Nothing was installed."
  say "ok  $f"
}

step "Release $RELEASE of $REPO"
[ -r /etc/os-release ] && . /etc/os-release || true
if [ "${ID:-}" != ubuntu ] || [ "${VERSION_ID:-}" != 24.04 ]; then
  say "NOTE: this is built and tested for Ubuntu 24.04 only; this system is ${PRETTY_NAME:-unknown}. Continuing is at your own risk."
fi
fetch "$WORK/SHA256SUMS" "$BASE/$RELEASE/SHA256SUMS"
fetch "$WORK/versions.lock" "$BASE/$RELEASE/versions.lock"
verify versions.lock

SDHT_VER=$(awk -F= '$1 == "sdht_version" { print $2 }' "$WORK/versions.lock")
[ -n "$SDHT_VER" ] || die "versions.lock has no sdht_version"
DEBS=(); CAM_VER=; CAM_URL=; CAM_SHA=; CAM_MEMBER=
while IFS=$'\t' read -r kind name ver file sha extra; do
  case "$kind" in
    deb) DEBS+=("$file"); [ "$(sum_of "$file")" = "$sha" ] || die "versions.lock and SHA256SUMS disagree about $file" ;;
    external) if [ "$name" = camilladsp ]; then CAM_VER=$ver; CAM_URL=$file; CAM_SHA=$sha; CAM_MEMBER=${extra:-camilladsp}; fi ;;
  esac
done < <(grep -v '^#' "$WORK/versions.lock" | grep -v '^[[:space:]]*$' | grep -v '^sdht_version')
[ ${#DEBS[@]} -gt 0 ] || die "versions.lock lists no packages"
DEBS+=("sdht_${SDHT_VER}_all.deb")      # the meta package contains versions.lock, so it cannot be listed in it; SHA256SUMS covers it
case "$CAM_URL" in https://github.com/HEnquist/camilladsp/releases/download/*) ;; *) [ "$CAMILLA" = 0 ] || die "versions.lock has no CamillaDSP entry from github.com/HEnquist/camilladsp" ;; esac

step "Plan"
say "Packages from this release (checked against SHA256SUMS before use):"
for f in "${DEBS[@]}"; do say "  $f   sha256 $(sum_of "$f")"; done
if [ "$CAMILLA" = 1 ]; then
  say "CamillaDSP $CAM_VER from $CAM_URL"
  say "  pinned sha256 $CAM_SHA  -> $CAMILLA_DIR/camilladsp (no sudo)"
else say "CamillaDSP: skipped (--no-camilladsp)"; fi
if [ "$(id -u)" = 0 ]; then say "sudo: not needed (you are root); apt-get install -y ./*.deb"
else say "sudo: ONE command, apt only:  sudo apt-get install -y ${DEBS[*]/#/./}"; fi
say "Not installed by this script: the player stack (Omniphony, harletty-bridge, mpv-omniphony). It is only checked below."
if [ "$DRY" = 1 ]; then
  step "Dry run"
  say "Fetched only SHA256SUMS and versions.lock (both verified/consistent). Nothing else was downloaded, installed or changed."
  exit 0
fi

if [ "$YES" = 0 ]; then
  [ -t 0 ] || die "no terminal to ask on; run it in a terminal or add --yes"
  read -r -p "Download, verify and install as planned? [y/N] " a; [ "$a" = y ] || [ "$a" = Y ] || die "stopped; nothing was installed"
fi

step "Download and verify"
for f in "${DEBS[@]}"; do fetch "$WORK/$f" "$BASE/$RELEASE/$f"; verify "$f"; done

step "Install the packages (sudo, apt only)"
cd "$WORK"
APT=(apt-get install -y)
for f in "${DEBS[@]}"; do APT+=("./$f"); done
if [ "$(id -u)" = 0 ]; then "${APT[@]}"
else
  command -v sudo >/dev/null 2>&1 || die "sudo not found; run this script as root or install the packages yourself"
  if [ "$YES" = 0 ]; then read -r -p "About to run: sudo ${APT[*]}   Continue? [y/N] " a; [ "$a" = y ] || [ "$a" = Y ] || die "stopped before sudo; the downloads are verified but nothing is installed"; fi
  sudo "${APT[@]}"
fi

if [ "$CAMILLA" = 1 ]; then
  step "CamillaDSP $CAM_VER"
  if command -v camilladsp >/dev/null 2>&1 && camilladsp --version 2>/dev/null | grep -q "$CAM_VER"; then
    say "already installed: $(command -v camilladsp) ($(camilladsp --version | head -1)); not touched"
  else
    arch=$(basename "$CAM_URL")
    fetch "$WORK/$arch" "$CAM_URL"
    got=$(sha256sum "$WORK/$arch" | awk '{print $1}')
    [ "$got" = "$CAM_SHA" ] || die "CamillaDSP checksum mismatch (pinned $CAM_SHA, download $got). Not installed."
    say "ok  $arch (matches the pinned sha256)"
    [ "$(tar -tzf "$WORK/$arch")" = "$CAM_MEMBER" ] || die "unexpected contents in $arch: $(tar -tzf "$WORK/$arch" | tr '\n' ' ')"
    mkdir -p "$WORK/cam" "$CAMILLA_DIR"
    tar -xzf "$WORK/$arch" -C "$WORK/cam" "$CAM_MEMBER"
    "$WORK/cam/$CAM_MEMBER" --version | grep -q "$CAM_VER" || die "the downloaded binary does not report version $CAM_VER"
    install -m 755 "$WORK/cam/$CAM_MEMBER" "$CAMILLA_DIR/camilladsp"
    say "installed $CAMILLA_DIR/camilladsp ($("$CAMILLA_DIR/camilladsp" --version | head -1))"
    case ":$PATH:" in *":$CAMILLA_DIR:"*) ;; *) say "NOTE: $CAMILLA_DIR is not on your PATH." ;; esac
    first=$(command -v camilladsp || true)
    [ "$first" = "$CAMILLA_DIR/camilladsp" ] || say "NOTE: 'camilladsp' on your PATH is $first, which comes before the one just installed."
  fi
fi

step "Player stack (checked only, never downloaded here)"
OA=${OA_HOME:-${HOME:-}/.local/opt/mpv-object-audio}
chk() { if [ -e "$1" ]; then say "present  $1"; else say "missing  $1"; fi; }
chk "$OA/bin/mpv"; chk "$OA/lib/liborender.so.0"
if ls "$OA"/lib/libharletty_*_bridge.so >/dev/null 2>&1; then say "present  harletty bridges in $OA/lib"; else say "missing  harletty bridges in $OA/lib"; fi
say "Omniphony, harletty-bridge and mpv-omniphony are other people's software. Nothing here downloads or redistributes them."
say "How to set them up: $DOCS/rebuild-checklist.md, and 'mpv-object-audio-install --dry-run' (installed by this release)."

step "Next steps"
cat <<'TXT'
  sdht-setup --dry-run install     see what the per-user setup would do (changes nothing)
  sdht-setup install               then do it (enables the router and the status page for your user)
  sdht-setup check                 report, including hand-installed copies in ~/.local/bin that would hide the packaged ones
  roomtone-layout --detect         describe your speaker layout (see /usr/share/doc/roomtone/layouts.md)
  Remove everything:               sdht-setup uninstall ; sudo apt-get purge sdht linux-theater-dsp roomtone seekthumbs mpv-shelf mpv-object-audio
This is a pre-release, tested only in simulation and on a clean Ubuntu 24.04 in CI; the packaging has not been run on the author's rig.
TXT
