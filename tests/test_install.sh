#!/usr/bin/env bash
# Tests install.sh against a fake release folder (file:// base) and a stand-in apt-get: dry run fetches only the two metadata files, a bad
# checksum stops everything before apt runs, a good release reaches apt with exactly the listed packages. No network, no real apt, no real sudo.
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
TAG=$(sed -n 's/^RELEASE=\(v[0-9.]*\).*/\1/p' "$(dirname "$0")/../install.sh"); V=${TAG#v}     # the release install.sh belongs to: the fake release below uses it
REL=$T/rel/$TAG; STUB=$T/stub; mkdir -p "$REL" "$STUB" "$T/home"
printf '#!/bin/sh\necho "$@" >> %s/apt.log\n' "$T" > "$STUB/apt-get"; chmod +x "$STUB/apt-get"
printf '#!/bin/sh\nexec "$@"\n' > "$STUB/sudo"; chmod +x "$STUB/sudo"   # the CI runner is not root: keep sudo from reaching the real apt
for n in linux-theater-dsp roomtone; do echo "fake $n" > "$REL/${n}_${V}_all.deb"; done
echo "fake sdht" > "$REL/sdht_${V}_all.deb"
{ printf '# test lock\nsdht_version=%s\n' "$V"
  for n in linux-theater-dsp roomtone; do printf 'deb\t%s\t%s\t%s_%s_all.deb\t%s\n' "$n" "$V" "$n" "$V" "$(sha256sum "$REL/${n}_${V}_all.deb" | cut -d' ' -f1)"; done; } > "$REL/versions.lock"
( cd "$REL" && sha256sum -- * > SHA256SUMS )
fail=0; ck() { if [ "$2" = ok ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
run() { PATH="$STUB:$PATH" HOME="$T/home" SDHT_BASE_URL="file://$T/rel" bash "$HERE/install.sh" "$@" 2>&1; }

out=$(run --dry-run --keep --no-camilladsp); rc=$?
ck "dry run exits 0" "$([ $rc = 0 ] && echo ok)"
ck "dry run prints the plan with the checksums" "$(echo "$out" | grep -q 'sha256 ' && echo "$out" | grep -q 'ONE command, apt only\|not needed' && echo ok)"
kept=$(echo "$out" | sed -n 's/^kept: //p')
ck "dry run fetched only SHA256SUMS and versions.lock" "$([ "$(ls "$kept" | sort | tr '\n' ' ')" = "SHA256SUMS versions.lock " ] && echo ok)"
ck "dry run never called apt" "$([ ! -e "$T/apt.log" ] && echo ok)"
rm -rf "$kept"

out=$(run --yes --no-camilladsp); rc=$?
ck "a good release exits 0" "$([ $rc = 0 ] && echo ok)"
ck "apt got exactly the three packages" "$([ "$(cat "$T/apt.log")" = "install -y ./linux-theater-dsp_${V}_all.deb ./roomtone_${V}_all.deb ./sdht_${V}_all.deb" ] && echo ok)"
ck "it says the player stack is only checked" "$(echo "$out" | grep -q 'never downloaded here' && echo ok)"
ck "it printed next steps" "$(echo "$out" | grep -q 'sdht-setup --dry-run install' && echo ok)"

rm -f "$T/apt.log"; echo "tampered" >> "$REL/roomtone_${V}_all.deb"
out=$(run --yes --no-camilladsp); rc=$?
ck "a tampered package stops the run (non-zero)" "$([ $rc != 0 ] && echo ok)"
ck "the mismatch is reported" "$(echo "$out" | grep -q "CHECKSUM MISMATCH for roomtone_${V}_all.deb" && echo ok)"
ck "apt was never called after a mismatch" "$([ ! -e "$T/apt.log" ] && echo ok)"

( cd "$REL" && echo "fake roomtone" > roomtone_${V}_all.deb && sed -i "s/^deb\tlinux-theater-dsp\t${V}\t\([^\t]*\)\t.*/deb\tlinux-theater-dsp\t${V}\t\1\t0000/" versions.lock && find . -type f ! -name SHA256SUMS -printf "%f\n" | sort | xargs sha256sum -- > SHA256SUMS )
out=$(run --yes --no-camilladsp); rc=$?
ck "a lock that disagrees with SHA256SUMS stops the run" "$([ $rc != 0 ] && echo "$out" | grep -q 'disagree' && echo ok)"

out=$(SDHT_BASE_URL="http://example.invalid" PATH="$STUB:$PATH" HOME="$T/home" bash "$HERE/install.sh" --dry-run 2>&1); rc=$?
ck "a non-https base address is refused" "$([ $rc != 0 ] && echo "$out" | grep -q 'non-https' && echo ok)"
ck "install.sh has no pipe into a shell and no eval" "$(! grep -nE '\| *(ba)?sh\b|\beval\b' "$HERE/install.sh" | grep -v '^[0-9]*:#' | grep -q . && echo ok)"
[ $fail = 0 ] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
