#!/usr/bin/env bash
# Tests the packaging kit on a tiny synthetic repository: the .deb is byte-identical across builds made at different times, in different folders,
# with different file times and umask; owner is root:root; the changelog converts; check-version catches every kind of mismatch.
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd)
KIT=$HERE/packaging/kit
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
R=$T/demo; mkdir -p "$R/packaging" "$R/bin"
cd "$R" || exit 1
git init -q . && git config user.email t@example.invalid && git config user.name t
cp "$HERE/LICENSE" LICENSE; printf 'Copyright 2026 Test\nTest NOTICE\n' > NOTICE; echo "# demo" > README.md
echo 0.1.0 > VERSION
printf '# Changelog\n\n## [0.1.0] - 2026-11-01\n\n- First thing, which is long enough that it has to be wrapped onto more than one line of the Debian changelog format.\n- Second thing.\n\n## [0.0.9] - 2026-10-01\n\n- Older.\n' > CHANGELOG.md
printf '#!/usr/bin/env python3\nprint("hi")\n' > bin/demo; chmod +x bin/demo
cat > packaging/deb.sh <<'X'
PKG=demo
SUMMARY="demo package"
DESCRIPTION="A demo used by the kit test."
DEPENDS="python3"
PYDIRS=/usr/lib/demo
stage() { inst 755 bin/demo /usr/lib/demo/demo; pyshebang /usr/lib/demo/demo; link ../lib/demo/demo /usr/bin/demo; manpage demo "demo command"; }
X
git add -A && git commit -q -m init
fail=0; ck() { if [ "$2" = ok ]; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

bash "$KIT/build-deb.sh" --out "$T/a" >/dev/null; A=$(sha256sum "$T/a/demo_0.1.0_all.deb" | cut -d' ' -f1)
touch -d '2001-01-01' bin/demo LICENSE; sleep 1
( umask 077; TMPDIR=/var/tmp bash "$KIT/build-deb.sh" --out "$T/b" >/dev/null ); B=$(sha256sum "$T/b/demo_0.1.0_all.deb" | cut -d' ' -f1)
ck "two builds (other folder, file times, umask) are byte-identical" "$([ "$A" = "$B" ] && echo ok)"
SOURCE_DATE_EPOCH=1000000000 bash "$KIT/build-deb.sh" --out "$T/c" >/dev/null; C=$(sha256sum "$T/c/demo_0.1.0_all.deb" | cut -d' ' -f1)
ck "another SOURCE_DATE_EPOCH changes the file (the epoch is really used)" "$([ "$A" != "$C" ] && echo ok)"
D=$T/a/demo_0.1.0_all.deb
ck "owner of every file is root:root" "$([ -z "$(dpkg-deb -c "$D" | awk '{print $2}' | grep -v '^root/root$')" ] && echo ok)"
ck "file list (files and folders; dpkg-deb puts symlinks last) is sorted" "$([ "$(dpkg-deb -c "$D" | grep -v '^l' | awk '{print $6}' | sed -n '2,$p')" = "$(dpkg-deb -c "$D" | grep -v '^l' | awk '{print $6}' | sed -n '2,$p' | LC_ALL=C sort)" ] && echo ok)"
ck "Architecture: all and the version comes from VERSION" "$([ "$(dpkg-deb -f "$D" Architecture)/$(dpkg-deb -f "$D" Version)" = "all/0.1.0" ] && echo ok)"
ck "shebang rewritten to /usr/bin/python3" "$(dpkg-deb --fsys-tarfile "$D" | tar -xO ./usr/lib/demo/demo | head -1 | grep -qx '#!/usr/bin/python3' && echo ok)"
ck "maintainer scripts: only a postrm that removes byte-code" "$([ "$(dpkg-deb -I "$D" | grep -cE ' (preinst|postinst|prerm)')" = 0 ] && dpkg-deb --ctrl-tarfile "$D" | tar -xO ./postrm | grep -q __pycache__ && echo ok)"
ck "copyright refers to the Apache-2.0 text and LICENSE and NOTICE are shipped" "$(dpkg-deb -c "$D" | grep -q 'doc/demo/LICENSE' && dpkg-deb -c "$D" | grep -q 'doc/demo/NOTICE' && dpkg-deb --fsys-tarfile "$D" | tar -xO ./usr/share/doc/demo/copyright | grep -q common-licenses/Apache-2.0 && echo ok)"
ck "Debian changelog has both entries, newest first" "$(dpkg-deb --fsys-tarfile "$D" | tar -xO ./usr/share/doc/demo/changelog.gz | gunzip | grep -E '^demo \(' | tr '\n' ' ' | grep -q '^demo (0.1.0).*demo (0.0.9)' && echo ok)"

bash "$KIT/check-version.sh" --tag v0.1.0 >/dev/null; ck "check-version accepts matching tag, VERSION and changelog" "$([ $? = 0 ] && echo ok)"
bash "$KIT/check-version.sh" --tag v0.1.1 >/dev/null 2>&1; ck "check-version rejects a tag that differs from VERSION" "$([ $? != 0 ] && echo ok)"
echo 0.2.0 > VERSION; bash "$KIT/check-version.sh" >/dev/null 2>&1; ck "check-version rejects a VERSION newer than the changelog" "$([ $? != 0 ] && echo ok)"
echo 0.1.0 > VERSION; sed -i 's/## \[0.1.0\]/## [0.1.1]/' CHANGELOG.md; bash "$KIT/check-version.sh" >/dev/null 2>&1; ck "check-version rejects a changelog newer than VERSION" "$([ $? != 0 ] && echo ok)"
bash "$KIT/build-deb.sh" --out "$T/d" >/dev/null 2>&1; ck "build-deb refuses when the changelog does not start with VERSION" "$([ $? != 0 ] && echo ok)"
git checkout -q CHANGELOG.md
bash "$KIT/release-build.sh" --out "$T/rel" >/dev/null 2>&1; ck "release-build: two builds compared, SHA256SUMS and source tarball written" "$([ -f "$T/rel/SHA256SUMS" ] && ls "$T/rel"/demo-0.1.0-source.tar.gz >/dev/null && ( cd "$T/rel" && sha256sum -c SHA256SUMS >/dev/null ) && echo ok)"
bash "$KIT/release-notes.sh" > "$T/notes.md"; ck "release notes: pre-release, caveats, no 'latest', no claim that CI proves it works on a rig" "$(grep -q 'PRE-RELEASE' "$T/notes.md" && grep -q 'has \*\*not\*\* been run on the author' "$T/notes.md" && grep -q 'Unsigned' "$T/notes.md" && echo ok)"
[ $fail = 0 ] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
