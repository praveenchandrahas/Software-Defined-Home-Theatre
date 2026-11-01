#!/usr/bin/env bash
# The main repository's own tests: shell syntax, the installed-vs-repo check, install.sh against a fake release, the packaging kit, Markdown links.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for f in scripts/*.sh scripts/preflight install.sh packaging/sdht-setup packaging/kit/*.sh; do bash -n "$f" && echo "ok $f"; done
bash tests/test_check_installed.sh
bash tests/test_install.sh
bash tests/test_kit.sh
python3 -I - <<'PY'
import re, pathlib, sys
bad = 0
for md in pathlib.Path('.').rglob('*.md'):
    for m in re.finditer(r'\]\((?!https?:|#|mailto:)([^)#\s]+)', md.read_text(errors='ignore')):
        if not (md.parent / m.group(1)).exists():
            print('broken link', md, '->', m.group(1)); bad += 1
sys.exit(1 if bad else 0)
PY
echo "main-repo tests OK"
