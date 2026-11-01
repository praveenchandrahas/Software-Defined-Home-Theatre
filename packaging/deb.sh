# shellcheck shell=bash disable=SC2034  # sourced by build-deb.sh, which uses these variables
# Package definition for kit/build-deb.sh (sourced). The meta package: it only depends on the exact component versions in versions.lock.
PKG=sdht
CHANGELOG_FILE=RELEASES.md
HOMEPAGE=https://github.com/praveenchandrahas/Software-Defined-Home-Theatre
SUMMARY="Software Defined Home Theatre: meta package and per-user setup"
DESCRIPTION="Installs the parts of the Software Defined Home Theatre project that are
packaged: linux-theater-dsp (router and DSP profile generator), roomtone
(measurement, autocal, status page), seekthumbs (seek-bar thumbnails),
mpv-shelf (film browser for mpv) and mpv-object-audio (wrapper and installer
for the player stack), each at the exact version listed in versions.lock.
.
Also ships the sdht-setup command, which runs the components' per-user setup
commands, and the project documentation. It does NOT install CamillaDSP (not
in Ubuntu's repositories; the sdht install.sh script fetches it with a
checksum) or the player stack (other people's software). Nothing is enabled,
started or written into a home folder by this package."
RECOMMENDS=
SUGGESTS=
PYDIRS=
# versions.lock: lines "deb<TAB>name<TAB>version<TAB>file<TAB>sha256"
DEPENDS=$(awk -F'\t' '$1=="deb" && $2!="sdht" { printf "%s%s (= %s)", sep, $2, $3; sep=", " }' "$REPO/versions.lock")
[ -n "$DEPENDS" ] || { echo "versions.lock lists no components" >&2; return 1 2>/dev/null || exit 1; }

stage() {
  inst 755 packaging/sdht-setup /usr/bin/sdht-setup
  inst 644 versions.lock /usr/share/sdht/versions.lock
  inst 644 docs/installation.md /usr/share/doc/sdht/installation.md
  inst 644 docs/rebuild-checklist.md /usr/share/doc/sdht/rebuild-checklist.md
  inst 644 docs/packaging.md /usr/share/doc/sdht/packaging.md
  manpage sdht-setup "run the per-user setup commands of the Software Defined Home Theatre components" "Subcommands: install, uninstall, check. Option: --dry-run (passed to every component)."
}
