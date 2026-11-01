#!/usr/bin/env bash
# Runs INSIDE a clean ubuntu:24.04 (container or chroot) as root. Installs the .deb file(s), runs the smoke test from the installed paths,
# removes and purges, and asserts that nothing is left behind:  ci-install-test.sh --deb A.deb [--deb B.deb] [--smoke SCRIPT [ARG]] [--repo DIR]
# Dependencies are installed first (so their files are not mistaken for ours); then the package must add NOTHING under /etc, /root, /home,
# /opt, /usr/local, /srv or /var/lib/systemd, and after `dpkg -r` and `dpkg -P` every file it listed must be gone.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive LC_ALL=C
DEBS=(); SMOKE=; SMOKE_ARG=
while [ $# -gt 0 ]; do
  case "$1" in
    --deb) DEBS+=("$2"); shift 2 ;;
    --smoke) SMOKE=$2; shift 2; if [ $# -gt 0 ] && [[ $1 != --* ]]; then SMOKE_ARG=$1; shift; fi ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done
[ ${#DEBS[@]} -gt 0 ] || { echo "need --deb" >&2; exit 2; }
fail() { echo "INSTALL-TEST FAIL: $*" >&2; exit 1; }
# shellcheck disable=SC1091
. /etc/os-release; echo "== environment: $PRETTY_NAME"
apt-get update -qq
apt-get install -y -qq --no-install-recommends ca-certificates >/dev/null

names=(); deps=()
for d in "${DEBS[@]}"; do names+=("$(dpkg-deb -f "$d" Package)"); done
for d in "${DEBS[@]}"; do
  for field in Depends Recommends; do
    v=$(dpkg-deb -f "$d" "$field" 2>/dev/null || true)
    while IFS= read -r dep; do
      dep=$(echo "$dep" | sed -e 's/(.*//' -e 's/|.*//' | tr -d ' ')
      [ -n "$dep" ] || continue
      skip=0; for n in "${names[@]}"; do [ "$dep" = "$n" ] && skip=1; done
      [ $skip = 1 ] || deps+=("$dep")
    done < <(echo "$v" | tr ',' '\n')
  done
done
echo "== installing dependencies first: ${deps[*]}"
apt-get install -y -qq "${deps[@]}" >/dev/null

snap() { find /etc /root /home /opt /usr/local /srv /var/lib/systemd -xdev \( -type f -o -type d -o -type l \) -printf '%p %y\n' 2>/dev/null | sort; }
snap > /tmp/snap0

echo "== installing ${DEBS[*]}"
apt-get install -y -qq "${DEBS[@]}" >/dev/null
for n in "${names[@]}"; do dpkg -s "$n" | grep -q '^Status: install ok installed' || fail "$n not installed"; done
dpkg -L "${names[@]}" | grep -v '^/\.$' | sort -u > /tmp/ownfiles
: > /tmp/roots
for n in "${names[@]}"; do for p in /usr/lib/"$n" /usr/share/doc/"$n" /usr/share/"$n"; do echo "$p" >> /tmp/roots; done; done

if [ -n "$SMOKE" ]; then
  echo "== smoke test from the installed paths: $SMOKE ${SMOKE_ARG}"
  bash "$SMOKE" ${SMOKE_ARG:+"$SMOKE_ARG"} || fail "smoke test"
fi
# what root running the installed scripts could leave behind next to them
for n in "${names[@]}"; do   # as root, python writes byte-code next to the modules it imports: simulate that, the postrm must remove it
  if [ -d /usr/lib/"$n" ]; then python3 -c "import glob,py_compile; [py_compile.compile(f, doraise=True) for f in glob.glob('/usr/lib/$n/*.py')]" 2>/dev/null || true; fi
done

snap > /tmp/snap1
diff /tmp/snap0 /tmp/snap1 >/tmp/snapdiff || { cat /tmp/snapdiff; fail "installing or running the package changed /etc, /root, /home, /opt, /usr/local, /srv or /var/lib/systemd"; }
PAT='systemctl|deb-systemd|invoke-rc|update-rc|camilla|pipewire|wireplumber|/home|~/|[$]HOME'
echo "== no maintainer script ran anything: none of enable/start was recorded"
for n in "${names[@]}"; do
  for s in preinst postinst prerm postrm; do
    f=/var/lib/dpkg/info/$n.$s
    if [ -f "$f" ] && grep -Eq "$PAT" "$f"; then
      grep -En "$PAT" "$f"; fail "$f touches services, audio config or a home folder"
    fi
  done
done

echo "== remove"
apt-get remove -y -qq "${names[@]}" >/dev/null
while IFS= read -r p; do
  [ -d "$p" ] && [ ! -L "$p" ] && continue          # directories may be shared (/usr/bin ...)
  [ -e "$p" ] || [ -L "$p" ] && fail "after remove, still present: $p"
done < /tmp/ownfiles
echo "== purge"
apt-get purge -y -qq "${names[@]}" >/dev/null
for n in "${names[@]}"; do if dpkg -l "$n" 2>/dev/null | grep -q '^[ir][icn]'; then fail "$n still known to dpkg"; fi; done
while IFS= read -r p; do [ -e "$p" ] && fail "after purge, still present: $p"; done < /tmp/roots
snap > /tmp/snap2
diff /tmp/snap0 /tmp/snap2 >/tmp/snapdiff || { cat /tmp/snapdiff; fail "purge left changes under /etc, /root, /home, ..."; }
left=$(find /usr/lib /usr/share /usr/bin -xdev \( -name '__pycache__' -path "*${names[0]}*" \) 2>/dev/null | head -3)
[ -z "$left" ] || fail "byte-code left behind: $left"
echo "INSTALL-TEST OK: ${names[*]}"
